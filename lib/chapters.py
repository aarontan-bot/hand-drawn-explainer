"""由 timeline.json 生成平台章节时间戳（YouTube/B站格式：mm:ss 标题）。

用法：python3 chapters.py <集目录> [--md <脚本md>] [--min-gap 20]
第一行固定 00:00 <EP.title>（取自 scripts/episode.js）。
随后每个 kind 不属于 title/end/illus/single 的镜头一行；
连续镜头若与上一章间隔（start 之差）< min-gap 秒则合并进上一章，不单独出一行。
标题 = 该镜「屏幕文字」各行（去掉 "- " 与 ①②③ 序号后）里长度 ≤ 14 字的最短一行；
没有这样的行（没有 md / 没有屏幕文字 / 各行都超过 14 字），就取 audio/shot-NN.txt 旁白前 12 字加"…"；
不管哪条路径，都不用超过 14 字的整句当章名。

--md 不给时先用 Project（从集目录往上找 series.json）自己找该集的脚本 md，找到就用并在 stderr
说明用了哪个文件；真找不到才退化成旁白摘录并警告。
"""
import argparse, json, re, sys
from pathlib import Path

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB))
import script_md
import project as project_mod
from project import Project

SKIP_KINDS = {'title', 'end', 'illus', 'single'}


def parse_episode_title(ep_dir):
    js_path = ep_dir / 'scripts/episode.js'
    if not js_path.exists():      # 老写法的集没有 episode.js，退化为空，由 --title 或集目录名兜底
        return ''
    js = js_path.read_text(encoding='utf-8')
    m = re.search(r'const\s+EP\s*=\s*\{(.*?)\}\s*;', js)
    if not m:
        return ''
    tm = re.search(r"title\s*:\s*(?:'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\")", m.group(1))
    return (tm.group(1) or tm.group(2) or '') if tm else ''


def resolve_md(ep_dir, md_arg):
    """--md 没给就用 Project 自己找；真找不到才退化成旁白摘录（保留原来的警告）。

    提示与警告都走 stderr：本脚本的 stdout 是章节文件正文。"""
    if md_arg:
        return Path(md_arg).resolve()
    proj = Project.from_episode_dir(ep_dir)
    no = project_mod.episode_no_of(ep_dir)
    md = proj.script_for(no) if (proj and no is not None) else None
    if md:
        print(f'提示：未给 --md，自动用 {md}', file=sys.stderr)
        return md
    print('警告：未给 --md 且没能自动找到脚本 md，章节名将退化成旁白摘录', file=sys.stderr)
    return None


MAX_TITLE_LEN = 14


def chapter_title(no, md_shots, ep_dir):
    if md_shots and no in md_shots:
        lines = md_shots[no].screen_items(strip_circled=True)
        candidates = [t for t in lines if t and len(t) <= MAX_TITLE_LEN]
        if candidates:
            return candidates[0]   # 第一行通常是标题；都超长时才退到旁白
    txt_path = ep_dir / f'audio/shot-{no:02}.txt'
    if txt_path.exists():
        text = txt_path.read_text(encoding='utf-8').strip()
        if text:
            return text[:12] + '…'
    return f'镜 {no}'


def fmt_ts(sec):
    sec = int(sec)
    return f'{sec // 60:02}:{sec % 60:02}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ep_dir')
    ap.add_argument('--md')
    ap.add_argument('--title', help='第一行章名；缺省取 episode.js 的 EP.title，再退化为集目录名')
    ap.add_argument('--min-gap', type=float, default=20)
    args = ap.parse_args()

    ep_dir = Path(args.ep_dir).resolve()
    timeline = json.loads((ep_dir / 'timeline.json').read_text())
    md_path = resolve_md(ep_dir, args.md)
    md_shots = script_md.parse(md_path).shots_by_no if md_path else None

    lines = [f"00:00 {args.title or parse_episode_title(ep_dir) or ep_dir.name}"]
    last_start = 0.0
    for scene in timeline['scenes']:
        if scene['kind'] in SKIP_KINDS:
            continue
        if scene['start'] - last_start < args.min_gap:
            continue
        title = chapter_title(scene['no'], md_shots, ep_dir)
        lines.append(f"{fmt_ts(scene['start'])} {title}")
        last_start = scene['start']

    print('\n'.join(lines))


if __name__ == '__main__':
    main()
