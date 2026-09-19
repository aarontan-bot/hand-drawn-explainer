#!/usr/bin/env python3
"""
默认阈值来源：提示词工程 9 集（203 镜）成片 P90：静止占比 0.95、最长静止 13 s（2026-09-18）。
成片静止段检测：「入场即停」判据（03-production.md §3.8：元素入场后不许整屏静止超过 13 秒）。

用法：
  单集：python3 motion_check.py <mp4> <timeline.json> [--step 3] [--thr 0.35] [--max-still 13.0] [--still-ratio 0.95]
  基线：python3 motion_check.py --baseline <系列目录> [--step 3] [--thr 0.35]
        对系列目录下所有 第*集/render/*_v1.mp4（没有 _v1 就取 render/ 下最新的 mp4）配它自己的
        timeline.json 逐集跑一遍，汇总全系列每镜「静止占比」「最长静止秒」的 P50/P90/max，
        并打印建议阈值（P90 向上取整）；只打印，不改 --max-still/--still-ratio 的默认值。

ffmpeg 每 --step 帧抽一张，灰度、缩到 320×180，只取内容区（安全区 y∈[130,860] 按 1080 等比映射到
180 高，约第 22–143 行），通过 rawvideo 管道读进 numpy（不落盘）。相邻抽样帧的内容区平均绝对差
（0–255 原始灰度尺度，见 still_intervals 的注释）< --thr 记一段「静止区间」；按 timeline.json 的
scenes 区间统计每镜静止占比与最长连续静止秒数；最长 > --max-still 或占比 > --still-ratio 标 ✗。
"""
import argparse
import json
import math
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

W, H = 320, 180
SAFE_TOP, SAFE_BOTTOM, FRAME_H = 130, 860, 1080
ROW_TOP = round(SAFE_TOP / FRAME_H * H)
ROW_BOTTOM = round(SAFE_BOTTOM / FRAME_H * H)

LIB = Path(__file__).resolve().parent
DEFAULT_MAX_STILL, DEFAULT_STILL_RATIO = 13.0, 0.95
try:
    THRESHOLDS = json.loads((LIB / 'metrics_thresholds.json').read_text(encoding='utf-8'))
except (OSError, json.JSONDecodeError):
    THRESHOLDS = {}


def probe_fps(mp4):
    out = subprocess.check_output([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=r_frame_rate', '-of', 'csv=p=0', str(mp4)
    ]).decode().strip()
    return float(Fraction(out))


def sample_frames(mp4, step):
    """每 step 帧取一张，灰度 320x180，从管道读 rawvideo，不落盘。返回 (times, frames[N,H,W] uint8)。"""
    fps = probe_fps(mp4)
    vf = f"select='not(mod(n\\,{step}))',scale={W}:{H},format=gray"
    cmd = ['ffmpeg', '-v', 'error', '-i', str(mp4), '-vf', vf, '-fps_mode', 'passthrough',
           '-f', 'rawvideo', '-pix_fmt', 'gray', '-']
    raw = subprocess.check_output(cmd)
    frame_bytes = W * H
    n = len(raw) // frame_bytes
    if n == 0:
        return [], np.zeros((0, H, W), dtype=np.uint8)
    arr = np.frombuffer(raw[:n * frame_bytes], dtype=np.uint8).reshape(n, H, W)
    times = [i * step / fps for i in range(n)]
    return times, arr


def still_intervals(times, frames, thr):
    """返回 [(t0,t1,still_bool), ...]，diff = 安全区内容区相邻帧的平均绝对差，0–255 原始灰度尺度
    （不按 255 归一化：手绘线稿大片纸白背景，真实动作时的平均差本来就很小，实测第 8 集成片
    P50≈0.004、P90≈0.37、max≈36（见开发时的校准），--thr 默认 0.35 落在这个尺度上才是有效阈值；
    若归一到 0–1，同样的默认值会把几乎所有帧对都判成静止，判据失效）。"""
    content = frames[:, ROW_TOP:ROW_BOTTOM, :].astype(np.float32)
    out = []
    for i in range(len(times) - 1):
        diff = float(np.abs(content[i + 1] - content[i]).mean())
        out.append((times[i], times[i + 1], diff < thr))
    return out


def scene_stats(intervals, start, end):
    """某镜时间范围内：静止占比、最长连续静止秒数（区间跨镜边界不算连续）。"""
    covered = [iv for iv in intervals if iv[0] >= start - 1e-6 and iv[1] <= end + 1e-6]
    still_time = sum(b - a for a, b, s in covered if s)
    longest, run = 0.0, 0.0
    for a, b, s in covered:
        if s:
            run += b - a
            longest = max(longest, run)
        else:
            run = 0.0
    duration = end - start
    ratio = still_time / duration if duration > 0 else 0.0
    return ratio, longest, duration


def percentile(values, p):
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * p
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] + (s[c] - s[f]) * (k - f)


def find_episode_mp4(ep_dir):
    """render/ 下优先找 *_v1.mp4；没有就取最新（按 mtime）的 *.mp4。"""
    render_dir = ep_dir / 'render'
    if not render_dir.exists():
        return None
    v1 = sorted(render_dir.glob('*_v1.mp4'))
    if v1:
        return v1[0]
    cands = sorted(render_dir.glob('*.mp4'), key=lambda p: p.stat().st_mtime)
    return cands[-1] if cands else None


def check_one(mp4, timeline_path, step, thr, max_still, still_ratio, print_table=True):
    """跑一集，返回 (rows, fail_count)；print_table=True 时顺带打印表。"""
    timeline = json.loads(Path(timeline_path).read_text(encoding='utf-8'))
    times, frames = sample_frames(mp4, step)
    if len(times) < 2:
        raise RuntimeError('抽到的帧数不足以比较（检查 mp4 路径/--step 是否过大）')
    intervals = still_intervals(times, frames, thr)
    if print_table:
        print('| 镜 | 时长 | 静止% | 最长静止 s | 判定 |')
        print('|---|---|---|---|---|')
    rows, fail = [], 0
    for s in timeline['scenes']:
        ratio, longest, duration = scene_stats(intervals, s['start'], s['end'])
        bad = longest > max_still or ratio > still_ratio
        fail += bad
        rows.append(dict(no=s['no'], duration=duration, ratio=ratio, longest=longest, bad=bad))
        if print_table:
            mark = '✗' if bad else '✓'
            print(f"| {s['no']} | {duration:.2f} | {ratio * 100:.0f}% | {longest:.2f} | {mark} |")
    return rows, fail, len(times)


def run_baseline(series_dirs, step, thr):
    all_ratios, all_longests = [], []
    errors = []
    for sd in series_dirs:
        sd = Path(sd)
        for ep in sorted(sd.glob('第*集')):
            tl_path = ep / 'timeline.json'
            if not tl_path.exists():
                continue
            mp4 = find_episode_mp4(ep)
            if not mp4:
                continue
            print(f'# {ep} -> {mp4.name}', file=sys.stderr)
            try:
                rows, fail, n_frames = check_one(mp4, tl_path, step, thr, max_still=10**9, still_ratio=10**9, print_table=False)
                for r in rows:
                    all_ratios.append(r['ratio'])
                    all_longests.append(r['longest'])
            except Exception as e:
                errors.append(f'{ep}：{type(e).__name__}: {e}')

    print(f'共 {len(all_ratios)} 镜（{len(errors)} 集出错）\n')
    for e in errors:
        print(f'错误：{e}')
    for label, vals, unit in (('静止占比', all_ratios, ''), ('最长静止秒', all_longests, 's')):
        if not vals:
            continue
        p50, p90, mx = percentile(vals, .5), percentile(vals, .9), max(vals)
        print(f'{label}：P50={p50:.3f}{unit} P90={p90:.3f}{unit} max={mx:.3f}{unit}')
    if all_ratios:
        print(f'\n建议阈值（P90 向上取整，不自动写回默认值）：--still-ratio ≈ {math.ceil(percentile(all_ratios, .9) * 100) / 100} '
              f'--max-still ≈ {math.ceil(percentile(all_longests, .9))}s')


def main():
    ap = argparse.ArgumentParser(description='成片静止段检测')
    ap.add_argument('mp4', nargs='?', help='成片 mp4（单集模式）')
    ap.add_argument('timeline', nargs='?', help='timeline.json（单集模式）')
    ap.add_argument('--step', type=int, default=3, help='每几帧抽一张（默认 3）')
    ap.add_argument('--thr', type=float, default=0.35, help='相邻抽样帧内容区平均绝对差阈值，判静止（默认 0.35）')
    ap.add_argument('--max-still', type=float, default=THRESHOLDS.get('max_still', DEFAULT_MAX_STILL), help='最长静止段秒数上限（默认 13.0）')
    ap.add_argument('--still-ratio', type=float, default=THRESHOLDS.get('still_ratio', DEFAULT_STILL_RATIO), help='静止占比上限（默认 0.95）')
    ap.add_argument('--baseline', metavar='系列目录', help='对系列目录下所有 第*集 跑一遍，输出静止占比/最长静止秒的分布与建议阈值')
    args = ap.parse_args()

    if args.baseline:
        run_baseline([args.baseline], args.step, args.thr)
        return

    if not args.mp4 or not args.timeline:
        ap.error('单集模式需要 <mp4> <timeline.json>，或改用 --baseline 系列目录')

    rows, fail, n_frames = check_one(args.mp4, args.timeline, args.step, args.thr, args.max_still, args.still_ratio)
    print(f'\n共 {len(rows)} 镜，{fail} 镜静止超标。')
    print(f'（抽帧：每 {args.step} 帧一张，共 {n_frames} 张；阈值 thr={args.thr} max-still={args.max_still}s still-ratio={args.still_ratio}）', file=sys.stderr)


if __name__ == '__main__':
    main()
