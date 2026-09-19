"""抓一帧成片 + 叠标题/副标/Logo，出一张 1920x1080 的封面图。

用法：python3 cover.py <集目录> <镜号> <输出png> [--title 文本] [--sub 文本] [--logo 路径] [--mp4 路径]
  --title/--sub 缺省从 <集目录>/scripts/episode.js 的 EP={...title:'…',sub:'…'} 取
  --mp4 缺省取 <集目录>/render/ 下修改时间最新的 mp4
  --logo 默认不叠：渲染出来的帧本来就带片头角标 Logo，再叠一次会重影；只有显式传 --logo 才画，没有自动查找。
抓帧时刻 = 该镜「画完」：events 非空取 min(end-0.5, max(events)+1.8)，否则 start+2.5。
标题/副标画在画面底部 y>=830 的条带里：条带铺满与画面底色一致的纯色（取 (10,10) 像素颜色），
盖掉原帧底部的字幕条与进度条，标题、副标都不再和画面主体重叠。
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

LIB = Path(__file__).resolve().parent
W, H = 1920, 1080

sys.path.insert(0, str(LIB))
import fonts

# 字重对齐 core.js 的片头：标题 font-weight 600 → Semibold，副标 400 → Regular。
# 字体怎么找见 fonts.py（苹方在 macOS 26 上搬进了带哈希的按需资源目录，写死路径会静默回退）。
def load_font(size, weight='Regular'):
    return fonts.cjk(size, weight)


def find_scene(timeline, no):
    for s in timeline['scenes']:
        if s['no'] == no:
            return s
    sys.exit(f'错误：timeline.json 里找不到第 {no} 镜')


def capture_time(scene):
    events = scene.get('events') or {}
    if events:
        t = min(scene['end'] - 0.5, max(events.values()) + 1.8)
    else:
        t = scene['start'] + 2.5
    return max(scene['start'], min(t, scene['end']))


def latest_mp4(ep_dir):
    cands = sorted((ep_dir / 'render').glob('*.mp4'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not cands:
        sys.exit(f'错误：{ep_dir / "render"} 下没有 mp4')
    return cands[0]


def extract_frame(mp4, t, out_png):
    subprocess.run([
        'ffmpeg', '-v', 'error', '-y', '-ss', str(t), '-i', str(mp4),
        '-frames:v', '1',
        '-vf', f'scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2',
        str(out_png),
    ], check=True)


def parse_episode_js(ep_dir):
    """从 scripts/episode.js 的 const EP={no:8,title:'…',sub:'…'}; 里取 title/sub；字符串可含另一种引号。"""
    js_path = ep_dir / 'scripts/episode.js'
    if not js_path.exists():      # 老写法的集没有 episode.js：靠 --title/--sub
        return '', ''
    js = js_path.read_text(encoding='utf-8')
    m = re.search(r'const\s+EP\s*=\s*\{(.*?)\}\s*;', js, re.S)
    if not m:
        return '', ''
    body = m.group(1)
    def field(name):
        fm = re.search(name + r"\s*:\s*(?:'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\")", body)
        return (fm.group(1) or fm.group(2) or '') if fm else ''
    return field('title'), field('sub')

def find_logo(arg_logo):
    """默认不叠 Logo（渲染帧自带片头角标），只有显式 --logo 才画。"""
    if not arg_logo:
        return None
    p = Path(arg_logo)
    return p if p.exists() else None


def paste_logo(img, logo_path, margin=40, width=260):
    """按透明有效边界裁切后等比缩到指定宽度，贴左上角，留 margin 边距。"""
    logo = Image.open(logo_path).convert('RGBA')
    alpha = logo.split()[-1]
    bbox = alpha.getbbox()
    if bbox:
        logo = logo.crop(bbox)
    ratio = width / logo.width
    logo = logo.resize((width, max(1, round(logo.height * ratio))), Image.LANCZOS)
    img.paste(logo, (margin, margin), logo)


BAND_TOP = 830
LEFT = 80


def draw_text_block(img, title, sub):
    """y>=830 到底部整幅铺一层与画面底色一致的纯色（取 (10,10) 像素颜色），盖掉原帧的字幕条/进度条；
    标题 96px + 副标 44px 画进这条带里，左边距 80，不再和画面主体重叠。"""
    title_font = load_font(96, 'Semibold')
    sub_font = load_font(44)

    bg = img.getpixel((10, 10))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, BAND_TOP, W, H], fill=bg)

    tb = draw.textbbox((0, 0), title, font=title_font) if title else (0, 0, 0, 0)
    sb = draw.textbbox((0, 0), sub, font=sub_font) if sub else (0, 0, 0, 0)
    title_h = tb[3] - tb[1]
    sub_h = sb[3] - sb[1] if sub else 0
    gap = 16 if (title and sub) else 0
    pad_top = 36

    y = BAND_TOP + pad_top
    if title:
        # 用真 Semibold 字重，不再靠 stroke 描边假装加粗（那会把笔画糊在一起）
        draw.text((LEFT, y), title, font=title_font, fill=(31, 29, 26, 255))
        y += title_h + gap
    if sub:
        draw.text((LEFT, y), sub, font=sub_font, fill=(80, 76, 68, 255))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ep_dir')
    ap.add_argument('shot_no', type=int)
    ap.add_argument('out_png')
    ap.add_argument('--title')
    ap.add_argument('--sub')
    ap.add_argument('--logo')
    ap.add_argument('--mp4')
    args = ap.parse_args()

    ep_dir = Path(args.ep_dir).resolve()
    timeline = json.loads((ep_dir / 'timeline.json').read_text())
    scene = find_scene(timeline, args.shot_no)
    t = capture_time(scene)
    mp4 = Path(args.mp4).resolve() if args.mp4 else latest_mp4(ep_dir)

    js_title, js_sub = parse_episode_js(ep_dir)
    title = args.title if args.title is not None else js_title
    sub = args.sub if args.sub is not None else js_sub

    out_png = Path(args.out_png).resolve()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    extract_frame(mp4, t, out_png)

    img = Image.open(out_png).convert('RGBA')
    draw_text_block(img, title, sub)
    logo_path = find_logo(args.logo)
    if logo_path:
        paste_logo(img, logo_path)
    img.convert('RGB').save(out_png)
    print(json.dumps(dict(out=str(out_png), shot=args.shot_no, t=round(t, 2), mp4=str(mp4), title=title, sub=sub, logo=str(logo_path) if logo_path else None), ensure_ascii=False))


if __name__ == '__main__':
    main()
