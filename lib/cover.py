"""从成片抓帧做封面：自动挑镜 → 框出内容真实边界 → 放大主体 → 按比例重新排版。

用法：python3 cover.py <集目录> <输出png> [--auto N | --shot 镜号] [--ratio 16:9|3:4]
                      [--title 文本] [--sub 文本] [--logo 路径] [--mp4 路径]
  不给 --shot 就默认 --auto 3：自动评分挑前 3 镜，出 <输出>_1.png…_3.png 供人挑一张。
  --title/--sub 缺省从 <集目录>/scripts/episode.js 的 EP={...title:'…',sub:'…'} 取。
  --mp4 缺省取 <集目录>/render/ 下修改时间最新的 mp4。
  --logo 缺省自动找 <集目录>/../assets/logo.png，找不到就不叠。

为什么不直接抓一帧当封面：
成片构图是为「边听边看」设计的——内容压在安全区 y∈[130,860] 内，底部留给字幕条，
所以任何一帧都是「主体偏上、四周大片空」。直接拿来当封面，主体小、重心沉，
列表缩略图里几乎看不清。这里的做法是把内容的真实包围盒框出来、放大，再把标题
摆进腾出的留白，而不是在原帧底部盖一条标题带。

怎么挑镜（--auto 的评分）：
`密度^1.5 × 方正度 × min(1, 主体高/500)`，三个量缺一不可——
- **密度** = 墨黑像素数 / 墨黑包围盒面积。实心角色密度高，线条图标密度低。
- **方正度** = 内容包围盒的 min(宽,高)/max(宽,高)。左右分离的构图在封面里天然吃亏，
  因为横向空间还要分一半给标题，等比缩放后主体会被压小。
- **主体高**压制异常值：扁横条（一行小格子）密度能到 0.3 却只有几十像素高，不能当封面。
单独用任何一个都会挑错：实测某集的总览图方正度最高（0.942）但最没有焦点，
而扁格子带密度最高（0.312）却是一条线。
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB))
import fonts

SAFE_TOP, SAFE_BOT = 130, 860      # 与 03-production §3 的安全区一致
BG_DIFF = 30                        # 与背景色的通道差之和超过它就算内容
INK_MAX = 60                        # 三通道都低于它算墨黑


# ---------------------------------------------------------------- 取帧与度量

def latest_mp4(ep_dir):
    cands = sorted((ep_dir / 'render').glob('*.mp4'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not cands:
        sys.exit(f'错误：{ep_dir / "render"} 下没有 mp4')
    return cands[0]


def grab(mp4, t, out_png):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t), '-i', str(mp4),
                    '-frames:v', '1', str(out_png)], check=True)
    return Image.open(out_png).convert('RGB')


def capture_time(scene):
    """该镜「画完」时刻：最后一个事件后 1.8 秒，但不越过镜尾。与 shot_metrics / review 同口径。"""
    events = scene.get('events') or {}
    t = min(scene['end'] - 0.5, max(events.values()) + 1.8) if events else scene['start'] + 2.5
    return max(scene['start'], min(t, scene['end']))


def content_bbox(img, pad=40):
    """内容的真实包围盒。只在安全区内找：Logo 角标、集数条、字幕条、进度条都在安全区外，自动避开。"""
    a = np.array(img)
    bg = a[10, 10].astype(int)
    reg = a[SAFE_TOP:SAFE_BOT].astype(int)
    mask = np.abs(reg - bg).sum(axis=2) > BG_DIFF
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return (0, SAFE_TOP, img.width, SAFE_BOT)
    return (max(0, xs.min() - pad), max(0, ys.min() + SAFE_TOP - pad),
            min(img.width, xs.max() + pad), min(img.height, ys.max() + SAFE_TOP + pad))


def score_frame(img):
    """返回 (得分, 读数)。公式与取舍见模块文档串。"""
    a = np.array(img)
    bg = a[10, 10].astype(int)
    reg = a[SAFE_TOP:SAFE_BOT]
    ink = (reg < INK_MAX).all(axis=2)
    n = int(ink.sum())
    if n < 300:                      # 几乎全白：片头片尾或空镜
        return 0.0, dict(ink=n)
    ys, xs = np.where(ink)
    bw, bh = int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)
    density = n / (bw * bh)
    m = np.abs(reg.astype(int) - bg).sum(axis=2) > BG_DIFF
    cy, cx = np.where(m)
    cw, ch = int(cx.max() - cx.min() + 1), int(cy.max() - cy.min() + 1)
    compact = min(cw, ch) / max(cw, ch)
    score = (density ** 1.5) * compact * min(1.0, bh / 500)
    return score, dict(density=round(density, 3), compact=round(compact, 3), subject_h=bh)


def rank_shots(ep_dir, mp4, tmp):
    """给全集镜头打分，返回按分降序的 [(score, no, t, 读数)]；片头片尾不参选。"""
    timeline = json.loads((ep_dir / 'timeline.json').read_text(encoding='utf-8'))
    out = []
    for s in timeline['scenes']:
        if s['kind'] in ('title', 'end'):
            continue
        t = round(capture_time(s), 2)
        img = grab(mp4, t, tmp)
        sc, meta = score_frame(img)
        if sc > 0:
            out.append((sc, s['no'], t, meta))
    out.sort(key=lambda r: -r[0])
    return out


# ---------------------------------------------------------------- 排版

def fit_font(draw, text, max_w, start, floor=64, weight='Semibold'):
    """标题长短不一，字号按可用宽度往下找——写死字号迟早溢出。"""
    size = start
    while size > floor:
        f = fonts.cjk(size, weight)
        if draw.textbbox((0, 0), text, font=f)[2] <= max_w:
            return f
        size -= 4
    return fonts.cjk(floor, weight)


def paste_logo(canvas, logo_path, xy, width):
    if not logo_path or not Path(logo_path).exists():
        return
    lg = Image.open(logo_path).convert('RGBA')
    bb = lg.split()[-1].getbbox()          # 透明底按有效边界裁切，不改原文件
    if bb:
        lg = lg.crop(bb)
    lg = lg.resize((width, max(1, round(lg.height * width / lg.width))), Image.LANCZOS)
    canvas.paste(lg, xy, lg)


def compose(src, title, sub, ratio, logo):
    """把抓到的帧重新构图：16:9 左文右图，3:4 上图下文。"""
    bg = tuple(int(v) for v in np.array(src)[10, 10])   # 画布底色取帧的真实底色，否则接缝处露白块
    crop = src.crop(content_bbox(src))

    if ratio == '3:4':
        W, H = 1080, 1440
        canvas = Image.new('RGB', (W, H), bg)
        aw, ah = int(W * 0.92), int(H * 0.60)
        r = min(aw / crop.width, ah / crop.height)
        nw, nh = int(crop.width * r), int(crop.height * r)
        canvas.paste(crop.resize((nw, nh), Image.LANCZOS), ((W - nw) // 2, int(H * 0.10) + (ah - nh) // 2))
        d = ImageDraw.Draw(canvas)
        tf = fit_font(d, title, int(W * 0.88), 96)
        sf = fonts.cjk(40)
        tb = d.textbbox((0, 0), title, font=tf)
        d.text(((W - (tb[2] - tb[0])) // 2, int(H * 0.745)), title, font=tf, fill=(31, 29, 26))
        sb = d.textbbox((0, 0), sub, font=sf)
        d.text(((W - (sb[2] - sb[0])) // 2, int(H * 0.745) + (tb[3] - tb[1]) + 34), sub, font=sf, fill=(120, 114, 104))
        paste_logo(canvas, logo, ((W - 200) // 2, 54), 200)
        return canvas

    W, H = 1920, 1080
    canvas = Image.new('RGB', (W, H), bg)
    ax, aw, ah = int(W * 0.46), int(W * 0.50), int(H * 0.82)
    r = min(aw / crop.width, ah / crop.height)
    nw, nh = int(crop.width * r), int(crop.height * r)
    canvas.paste(crop.resize((nw, nh), Image.LANCZOS), (ax + (aw - nw) // 2, (H - nh) // 2))
    d = ImageDraw.Draw(canvas)
    tx = 112
    tf = fit_font(d, title, int(W * 0.46) - tx - 40, 108)
    sf = fonts.cjk(40)
    tb = d.textbbox((0, 0), title, font=tf)
    th = tb[3] - tb[1]
    y = (H - th - 30 - 44) // 2
    d.text((tx, y), title, font=tf, fill=(31, 29, 26))
    d.text((tx, y + th + 30), sub, font=sf, fill=(120, 114, 104))
    paste_logo(canvas, logo, (tx, 64), 230)
    return canvas


# ---------------------------------------------------------------- 入口

def parse_episode_js(ep_dir):
    """从 scripts/episode.js 的 const EP={no:8,title:'…',sub:'…'}; 取 title/sub；字符串可含另一种引号。"""
    js_path = ep_dir / 'scripts/episode.js'
    if not js_path.exists():
        return '', ''
    m = re.search(r'const\s+EP\s*=\s*\{(.*?)\}\s*;', js_path.read_text(encoding='utf-8'), re.S)
    if not m:
        return '', ''
    body = m.group(1)

    def field(name):
        fm = re.search(name + r"\s*:\s*(?:'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\")", body)
        return (fm.group(1) or fm.group(2) or '') if fm else ''
    return field('title'), field('sub')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ep_dir')
    ap.add_argument('out_png')
    ap.add_argument('--shot', type=int, help='指定镜号；不给就自动挑')
    ap.add_argument('--auto', type=int, default=3, metavar='N', help='自动挑分最高的 N 镜各出一张（默认 3）')
    ap.add_argument('--ratio', default='16:9', choices=['16:9', '3:4'])
    ap.add_argument('--title')
    ap.add_argument('--sub')
    ap.add_argument('--logo')
    ap.add_argument('--mp4')
    a = ap.parse_args()

    ep_dir = Path(a.ep_dir).resolve()
    mp4 = Path(a.mp4).resolve() if a.mp4 else latest_mp4(ep_dir)
    out_png = Path(a.out_png).resolve()
    out_png.parent.mkdir(parents=True, exist_ok=True)

    js_title, js_sub = parse_episode_js(ep_dir)
    title = a.title if a.title is not None else js_title
    sub = a.sub if a.sub is not None else js_sub
    logo = a.logo or (ep_dir.parent / 'assets/logo.png')

    tmp = out_png.parent / f'_cover_tmp_{out_png.stem}.png'
    try:
        if a.shot is not None:
            timeline = json.loads((ep_dir / 'timeline.json').read_text(encoding='utf-8'))
            scene = next((s for s in timeline['scenes'] if s['no'] == a.shot), None)
            if scene is None:
                sys.exit(f'错误：timeline.json 里找不到第 {a.shot} 镜')
            picks = [(None, a.shot, round(capture_time(scene), 2), {})]
        else:
            picks = rank_shots(ep_dir, mp4, tmp)[:max(1, a.auto)]
            if not picks:
                sys.exit('错误：没有可用镜头（全是空画面？）')

        results = []
        for i, (sc, no, t, meta) in enumerate(picks, 1):
            img = compose(grab(mp4, t, tmp), title, sub, a.ratio, logo)
            dst = out_png if len(picks) == 1 else out_png.with_name(f'{out_png.stem}_{i}{out_png.suffix}')
            img.save(dst)
            results.append(dict(out=str(dst), shot=no, t=t, score=(round(sc, 4) if sc else None), **meta))
    finally:
        tmp.unlink(missing_ok=True)

    print(json.dumps(dict(ratio=a.ratio, title=title, sub=sub, mp4=str(mp4),
                          logo=str(logo) if Path(logo).exists() else None,
                          picks=results), ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
