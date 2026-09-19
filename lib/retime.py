"""按旁白实测字数重排每镜时间段，并回填本集卡片的时长与字数。

用法：python3 retime.py <脚本目录> [--glob 'N.*.md'] [--check]
  默认匹配目录下除 00- 开头外的所有 *.md，按文件名排序。
  --check 只比对不改写：时间码或卡片字数与实算不一致就非 0 退出（交付前自检用）。
          「有没有跑过 retime」过去没有任何机器检查，靠人记得敲。

规则（与全课设定 §脚本格式约定一致）：
  语速 300 字/分钟（＝ 0.2 秒/字，字数不含标点空白）
  插画镜另加 1.5 秒画面停留，程序镜另加 0.5 秒，「停顿」另计（一镜多处停顿求和）
  旁白为空的镜：片头固定 5 秒，片尾固定 3 秒
实际时间以配音后的时间轴为准，本脚本只保证脚本内部自洽。

分镜解析走 lib/script_md.py。缺「## 出图清单」的脚本（全程序镜的一集）过去在这里
ValueError 崩掉，现在按 tail 为空处理，照常改写。
"""
import argparse, re, sys
from pathlib import Path

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB))
import script_md

CARD_ROW_RE = re.compile(r'\| 时长 \| .*? \|')


def mmss(t):
    return f'{int(t)//60}:{int(t)%60:02d}'


def shot_duration(shot):
    """该镜时长（秒）。旁白为空的镜按片头 5 秒 / 片尾 3 秒。"""
    chars = shot.narration_chars
    if chars == 0:
        return 5.0 if '片头' in shot.raw else 3.0
    pause = shot.pause_seconds or 0
    return chars / 5 + (1.5 if shot.method == '插画' else 0.5) + pause


def retime_one(sc):
    """返回 (新正文, 卡片时长行内容, 总秒数, 总字数, [(镜号, 原时间段, 实算时间段)])。"""
    preamble, blocks = script_md.split_shot_blocks(sc.body)
    out, t, total_chars, changes = [preamble], 0.0, 0, []
    for shot, blk in zip(sc.shots, blocks):
        dur = shot_duration(shot)
        span = f'{mmss(t)}–{mmss(t + dur)}'
        # 原样保留第 1 段与第 3 段之后的所有分段，只换时间段那一段
        parts = list(shot.head_parts)
        while len(parts) < 2:
            parts.append('')
        parts[1] = span
        rest = blk.split('\n', 1)
        out.append(script_md.SEP.join(parts) + ('\n' + rest[1] if len(rest) > 1 else ''))
        if shot.span != span:
            changes.append((shot.no, shot.span, span))
        t += dur
        total_chars += shot.narration_chars
    body = '### '.join(out) if blocks else preamble
    return body, f'预计时长：约 {mmss(t)} ｜ 旁白字数：{total_chars} 字', t, total_chars, changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('--glob', default=None)
    ap.add_argument('--check', action='store_true',
                    help='只比对不改写；有任何不一致就以退出码 1 结束')
    args = ap.parse_args()
    root = Path(args.dir).resolve()
    # 第一个参数是脚本「目录」。传成单个 md 时 glob 匹配不到任何东西，原来就这么静默 rc=0 退出，
    # 用的人以为回填过了，其实时间码还是手估的（手估字数系统性偏高，见 gotchas）
    if root.is_file():
        files = [root] if root.suffix == '.md' else []
        if not files:
            raise SystemExit(f'错误：{root} 不是 .md')
    elif not root.is_dir():
        raise SystemExit(f'错误：找不到脚本目录 {root}')
    else:
        files = script_md.iter_script_files(root, args.glob)
    if not files:
        raise SystemExit(f'错误：{root} 下没有匹配到脚本 md（--glob {args.glob!r}）' if args.glob
                         else f'错误：{root} 下没有脚本 md（除 00- 开头外的 *.md）')

    stale = []
    for f in files:
        sc = script_md.parse(f)
        if not sc.shots:
            print(f'{f.name}  跳过：没有解析出分镜', file=sys.stderr)
            continue
        body, card_value, t, total_chars, changes = retime_one(sc)

        if args.check:
            bad = []
            if changes:
                bad.append(f'{len(changes)} 个镜的时间段与实算不符'
                           f'（首个：镜 {changes[0][0]} 脚本 {changes[0][1]} ≠ 实算 {changes[0][2]}）')
            card_now = (sc.card.get('时长') or '').strip()
            if card_now != card_value:
                bad.append(f'卡片时长行不符：脚本 {card_now!r} ≠ 实算 {card_value!r}')
            if bad:
                stale.append(f.name)
                print(f'FAIL  {f.name}：' + '；'.join(bad))
            else:
                print(f'OK    {f.name}  {total_chars} 字  {mmss(t)}')
            continue

        head = CARD_ROW_RE.sub(f'| 时长 | {card_value} |', sc.head, count=1)
        f.write_text(head + body + sc.tail, encoding='utf-8')
        print(f'{f.name}  {total_chars} 字  {mmss(t)}')

    if args.check and stale:
        print(f'\n{len(stale)} 份脚本的时间码没回填过或已过期：{", ".join(stale)}', file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
