"""系列进度表：维护 <系列目录>/进度.md 里的「集 × 阶段」表格，不存在就创建，存在就只改对应格。

用法：python3 progress.py <系列目录> <集号> <阶段> <状态>
  阶段只能是：脚手架 配音 插画 程序动画 check 渲染 终审 交付
  状态是任意短文本，如 "✅ 09-18" "⏳" "❌ 缺 3 张"
其它脚本（scaffold_episode.py、synthesize.py、build.py）在各自阶段完成时会 import 本模块调用 update()。
"""
import sys
from pathlib import Path

COLUMNS = ['脚手架', '配音', '插画', '程序动画', 'check', '渲染', '终审', '交付']


def _parse(text):
    rows, order = {}, []
    lines = [l for l in text.splitlines() if l.strip().startswith('|')]
    for line in lines[2:]:  # 跳过表头与分隔行
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if not cells or not cells[0]:
            continue
        ep = cells[0]
        if ep.isdigit():
            ep = f'第{ep}集'
        vals = (cells[1:] + [''] * len(COLUMNS))[:len(COLUMNS)]
        rows[ep] = vals
        order.append(ep)
    return rows, order


def _render(rows, order):
    head = '| 集 | ' + ' | '.join(COLUMNS) + ' |'
    sep = '|' + '---|' * (len(COLUMNS) + 1)
    lines = [head, sep]
    for ep in order:
        lines.append('| ' + ep + ' | ' + ' | '.join(rows[ep]) + ' |')
    return '\n'.join(lines) + '\n'


def update(series_dir, episode, stage, status):
    series_dir = Path(series_dir)
    # 集号统一成「第N集」：其它脚本 import 时传的是目录名（第1集），命令行常传裸数字（1），
    # 不归一会在表里长出两行同一集
    episode = str(episode).strip()
    if episode.isdigit():
        episode = f'第{episode}集'
    if stage not in COLUMNS:
        raise SystemExit(f'错误：未知阶段「{stage}」，只能是 {"/".join(COLUMNS)}')
    p = series_dir / '进度.md'
    if p.exists():
        existing = p.read_text(encoding='utf-8')
        header = existing.split('\n', 1)[0]
        rows, order = _parse(existing)
    else:
        header = '# 进度表'
        rows, order = {}, []
    if episode not in rows:
        rows[episode] = [''] * len(COLUMNS)
        order.append(episode)
    rows[episode][COLUMNS.index(stage)] = status
    series_dir.mkdir(parents=True, exist_ok=True)
    p.write_text(header + '\n\n' + _render(rows, order), encoding='utf-8')
    print(f'已更新 {p}：{episode} / {stage} = {status}')


if __name__ == '__main__':
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    update(*sys.argv[1:])
