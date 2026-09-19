"""按固定间隔从成片抽帧拼成联系表，用来看「动作过程」。

用法：python3 filmstrip.py <成片mp4> <输出png前缀> [--every 2.4] [--cols 3] [--rows 3] [--width 640]
  每张图最多 cols×rows 格，超出自动分成 <前缀>_01.png、<前缀>_02.png……
  每格左上角烧上该帧的时刻，方便对着 timeline.json 定位是哪一镜。

为什么要它：review.py 每镜只抓「画完」那一帧，shot_metrics.py 每镜也只采一个时刻，
两者结构上都看不见只在动画过程中出现的错误——元素落在半路、两个 tween 抢同一个属性、
opacity 被后画的元素盖回去。这类问题到「画完时刻」已经复原，必须密集抽帧才看得出来。
（2026-09-18 的测试片就是这样漏掉一个 dim 失效的 bug，终审 9 宫格全绿。）

间隔怎么选：默认 2.4 秒，一分钟的片子出 3 张九宫格。镜头短、动作密的片子调到 1.5－2 秒；
只想粗看流动用 4 秒。抽出来的每一张都要真的用 Read 看，不看等于没跑。
"""
import argparse, subprocess, sys, tempfile, shutil
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fonts


def load_font(size):
    return fonts.mono(size)


def duration(mp4):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'csv=p=0', str(mp4)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mp4')
    ap.add_argument('out_prefix', help='输出前缀，会生成 <前缀>_01.png 等')
    ap.add_argument('--every', type=float, default=2.4, help='抽帧间隔秒数（默认 2.4）')
    ap.add_argument('--cols', type=int, default=3, help='每张图几列（默认 3）')
    ap.add_argument('--rows', type=int, default=3, help='每张图几行（默认 3）')
    ap.add_argument('--width', type=int, default=640, help='每格宽度像素（默认 640）')
    a = ap.parse_args()

    mp4 = Path(a.mp4).resolve()
    if not mp4.is_file():
        raise SystemExit(f'错误：找不到成片 {mp4}')
    if a.every <= 0:
        raise SystemExit('错误：--every 要大于 0')
    prefix = Path(a.out_prefix).resolve()
    prefix.parent.mkdir(parents=True, exist_ok=True)

    tmp = Path(tempfile.mkdtemp(prefix='filmstrip_'))
    try:
        cmd = ['ffmpeg', '-y', '-v', 'error', '-i', str(mp4),
               '-vf', f'fps=1/{a.every},scale={a.width}:-1',
               '-fps_mode', 'passthrough', str(tmp / 'f_%04d.png')]
        r = subprocess.run(cmd, capture_output=True, text=True)
        frames = sorted(tmp.glob('f_*.png'))
        if not frames:
            raise SystemExit(f'错误：一帧都没抽到（ffmpeg: {r.stderr.strip()[:200]}）')

        W, H = Image.open(frames[0]).size
        font = load_font(max(18, W // 26))
        per = a.cols * a.rows
        pages = [frames[i:i + per] for i in range(0, len(frames), per)]
        total = duration(mp4)

        print(f'| 图 | 覆盖时刻 | 格数 |')
        print(f'|---|---|---|')
        for pi, page in enumerate(pages, 1):
            rows_needed = (len(page) + a.cols - 1) // a.cols
            sheet = Image.new('RGB', (a.cols * W, rows_needed * H), '#9A9A9A')
            d = ImageDraw.Draw(sheet)
            for i, f in enumerate(page):
                x, y = (i % a.cols) * W, (i // a.cols) * H
                sheet.paste(Image.open(f).convert('RGB'), (x, y))
                t = (frames.index(f)) * a.every
                label = f'{t:.1f}s'
                tw = d.textlength(label, font=font)
                d.rectangle([x + 8, y + 8, x + 16 + tw + 8, y + 8 + font.size + 12], fill='#FFFFFF')
                d.text((x + 16, y + 14), label, fill='#1E1C1A', font=font)
            out = prefix.with_name(f'{prefix.name}_{pi:02}.png')
            sheet.save(out)
            t0 = (frames.index(page[0])) * a.every
            t1 = (frames.index(page[-1])) * a.every
            print(f'| {out} | {t0:.1f}–{t1:.1f}s | {len(page)} |')
        print(f'\n成片 {total:.1f}s，每 {a.every}s 一帧，共 {len(frames)} 帧 / {len(pages)} 张。'
              f'每张都要用 Read 真的看过才算跑完。')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
