#!/usr/bin/env python3
"""脚本 md 解析器的行为锁：把 lib/script_md.py 的口径钉死在明确的期望值上。

为什么需要它：smoke.sh 第 1、2 项拿真实的 9 集做字节级 oracle，但那 9 份脚本高度同质——
203 个镜头头全是 3 段式、零个半角冒号、零个重复「停顿」、零个多行旁白、64 行出图清单全是三列。
也就是说 oracle 只跑得到 happy path。7 份解析器当初的口径分歧，恰恰全在 oracle 照不到的地方。
在一个只有三列表的语料上拿到「全部 PASS」，和 lint_script.py 不带白名单跑出来的绿灯是同一种东西。

fixtures/ 下的合成夹具逐个覆盖那些照不到的地方：两列出图清单表、缺「## 出图清单」、
字段多行续行、4 段式镜头头、未登记字段名、块内重复「停顿」、缺「## 分镜」。

用法：python3 evals/parser_diff.py          # 全部通过退出码 0，任一条不过退出码 1
"""
import re
import sys
from pathlib import Path

EVALS = Path(__file__).resolve().parent
SKILL = EVALS.parent
FIX = EVALS / 'fixtures'
sys.path.insert(0, str(SKILL / 'lib'))

import script_md
from script_md import parse, split_sections, narration_chars, find_episode_md

FAILS = []
CHECKS = [0]


def check(cond, label, detail=''):
    CHECKS[0] += 1
    if not cond:
        FAILS.append(f'{label}' + (f'\n      {detail}' if detail else ''))


def eq(got, want, label):
    check(got == want, label, f'got={got!r}\n      want={want!r}')


def fx(name):
    return parse(FIX / name)


# ---------------------------------------------------------------- 不变式：head+body+tail == 原文
def test_roundtrip():
    mds = sorted(FIX.glob('*.md'))
    check(len(mds) >= 7, '夹具数量', f'只找到 {len(mds)} 份，期望 ≥7')
    for p in mds:
        text = p.read_text(encoding='utf-8')
        h, b, t = split_sections(text)
        eq(h + b + t, text, f'切分不变式 head+body+tail == 原文（{p.name}）')


# ---------------------------------------------------------------- 01 两列出图清单表
def test_two_col_table():
    s = fx('01-two-col-table.md')
    rows = s.illus_rows
    eq(sorted(rows), [2, 3, 4, 5, 6], '两列表：解析出的镜号')

    eq((rows[2].kind, rows[2].left, rows[2].right),
       ('illus', '一只小猫蹲在窗台上', '同一只小猫跳到桌子上'), '两列表：分两层 → 左右')
    eq((rows[3].kind, rows[3].left, rows[3].right),
       ('single', '一张摊开的地图铺满画面中央', ''), '两列表：单场景居中 → 单幅')
    eq((rows[4].kind, rows[4].left, rows[4].right),
       ('single', '一把旧钥匙躺在木头桌面上，旁边是一枚硬币', ''), '两列表：无标记整段 → 单幅')
    eq((rows[5].kind, rows[5].left, rows[5].right, rows[5].merged_three),
       ('illus', '出发的小船', '海上的风浪；靠岸的小船', True), '两列表：分三层 → 中层并入右岛')
    eq((rows[6].kind, rows[6].left, rows[6].right),
       ('illus', '一棵光秃秃的树', '同一棵树长满叶子'), '两列表：左边/右边 写法')

    # 单幅的 right 是空串不是 None：扫描类调用方直接 zip cells，不该碰到 None
    for no, r in rows.items():
        check(r.right is not None, f'两列表：镜 {no} 的 right 不是 None')
        eq(len(r.cells), 2, f'两列表：镜 {no} 的 cells 是两格')

    # 出图清单表体不许把「## 知识点对账」的表格行收进来
    check(99 not in rows and all(n <= 7 for n in rows), '两列表：没有误收对账表的行', str(sorted(rows)))


# ---------------------------------------------------------------- 02 缺出图清单
def test_no_illus_section():
    s = fx('02-no-illus-section.md')          # 不抛异常本身就是断言
    eq(s.tail, '', '缺出图清单：tail 为空')
    eq(s.illus_rows, {}, '缺出图清单：illus_rows 为空 dict')
    eq(len(s.shots), 3, '缺出图清单：仍然解析出 3 镜')
    eq(s.shots[1].screen_items(), ['没有插画', '全程程序层'], '缺出图清单：屏幕文字照常解析')
    text = (FIX / '02-no-illus-section.md').read_text(encoding='utf-8')
    eq(s.render(), text, '缺出图清单：render() 能原样拼回（retime 改写靠这个）')


# ---------------------------------------------------------------- 03 多行续行
def test_multiline_fields():
    s = fx('03-multiline-fields.md')
    sh = s.shot(2)
    check('第二行' in sh.narration, '多行续行：旁白第二行没丢', repr(sh.narration))
    eq(sh.narration.count('\n'), 1, '多行续行：旁白是两行')
    check('右栏后出现' in sh.field('画面'), '多行续行：画面第二行没丢')
    # 只取一行的老口径会少算第二行的字数
    one_line_only = narration_chars(sh.narration.split('\n')[0])
    check(sh.narration_chars > one_line_only,
          '多行续行：字数把第二行算进去了', f'两行={sh.narration_chars} 一行={one_line_only}')

    eq(sh.screen_items(), ['①第一条屏幕文字', '②第二条屏幕文字', '③第三条屏幕文字'],
       '多行续行：屏幕文字逐条（保留序号）')
    eq(sh.screen_items(strip_circled=True), ['第一条屏幕文字', '第二条屏幕文字', '第三条屏幕文字'],
       '多行续行：屏幕文字逐条（去序号）')
    eq(s.shot(3).screen_items(), ['单行内联的屏幕文字'], '单行内联屏幕文字')


# ---------------------------------------------------------------- 04 镜头头段数异常
def test_odd_headers():
    s = fx('04-odd-headers.md')               # 不抛异常本身就是断言
    eq([x.no for x in s.shots], [1, 2, 3, 4], '异常头：四镜都在')
    # 4 段式：做法取第 3 段，不是最后一段（shots_dump.py 过去取 parts[-1]）
    eq(s.shot(2).method, '插画', '异常头：4 段式做法取第 3 段')
    check('备注' not in s.shot(2).method, '异常头：没把第 4 段当成做法')
    # 2 段式：缺做法不许崩，返回空串
    eq(s.shot(3).method, '', '异常头：2 段式做法为空串')
    eq(s.shot(3).span, '0:20–0:35', '异常头：2 段式时间段仍取到')
    # 多余分段必须原样留在 head_parts 里，retime 改写时不能丢
    eq(len(s.shot(2).head_parts), 4, '异常头：head_parts 保留全部分段')


# ---------------------------------------------------------------- 05 未登记字段名
def test_unknown_field():
    s = fx('05-unknown-field.md')
    sh = s.shot(2)
    # 白名单式解析会把「备注」连同后面的字段一起吞进旁白
    eq(sh.narration, '这一句才是旁白。', '未登记字段：旁白没被备注污染')
    check('备注' in sh.fields, '未登记字段：备注自成一个字段', str(sorted(sh.fields)))
    check('制作看的说明' not in sh.narration, '未登记字段：备注正文没混进旁白')
    eq(sh.screen_items(), ['只有这一条'], '未登记字段：屏幕文字没被上一字段吞掉')
    eq(sh.narration_chars, narration_chars('这一句才是旁白。'), '未登记字段：字数没虚高')


# ---------------------------------------------------------------- 06 停顿
def test_pause():
    s = fx('06-dup-pause.md')
    eq(s.shot(2).pause_seconds, 1.5, '停顿：单个小数')
    eq(s.shot(3).pause_seconds, 3, '停顿：块内两处求和')
    eq(s.shot(4).pause_seconds, 2, '停顿：没有空格的 "2秒" 也认')
    # int / float 字面形态要保留，否则 shots.json 的字节会变
    check(isinstance(s.shot(4).pause_seconds, int), '停顿：整数秒返回 int 不是 float',
          repr(s.shot(4).pause_seconds))
    check(isinstance(s.shot(2).pause_seconds, float), '停顿：小数秒返回 float')
    eq(s.shot(1).pause_seconds, None, '停顿：没有停顿字段返回 None')
    # 省略号 = 停顿在旁白中间，不能自动转 pause_end
    eq(s.shot(5).pause_mid_sentence, True, '停顿：旁白中间的停顿被识别')
    eq(s.shot(2).pause_mid_sentence, False, '停顿：镜尾停顿不算中间')


# ---------------------------------------------------------------- 07 缺分镜
def test_no_shots_section():
    s = fx('07-no-shots-section.md')          # 不抛异常本身就是断言
    eq(s.shots, [], '缺分镜：返回空 shots 列表')
    eq(s.illus_rows, {}, '缺分镜：illus_rows 为空')
    check(s.card.get('单元') == 'A 夹具', '缺分镜：本集卡片照常解析', str(s.card))


# ---------------------------------------------------------------- 字数口径
def test_narration_chars():
    eq(narration_chars('你好，世界。'), 4, '字数：去标点')
    eq(narration_chars('你好 世界'), 4, '字数：去空白')
    eq(narration_chars('（无旁白，片头）'), 0, '字数：（无… 的镜算 0')
    eq(narration_chars(''), 0, '字数：空串算 0')
    eq(narration_chars(None), 0, '字数：None 算 0')
    # 只去空白的老口径（preview_pack 过去那份）会把标点也算成字
    s = '你好，世界。'
    check(narration_chars(s) < len(re.sub(r'\s', '', s)), '字数：比只去空白的口径小')


# ---------------------------------------------------------------- 标题两种语义
def test_titles():
    s = fx('01-two-col-table.md')
    eq(s.title, '1.1　两列出图清单表', '标题：H1 整行原文')
    eq(s.title_short, '两列出图清单表', '标题：砍掉首个 token')


# ---------------------------------------------------------------- 按集号找脚本
def test_find_episode_md():
    eq(find_episode_md(FIX, 1).name, '01-two-col-table.md', '找脚本：01- 命名')
    eq(find_episode_md(FIX, 99), None, '找脚本：找不到返回 None')
    eq(find_episode_md(FIX / '不存在', 1), None, '找脚本：目录不存在返回 None')

    # 三种命名都要认。3.8- 这种「单元.集」命名过去取到的是单元号，按集号永远找不到文件
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        for name in ('00-全片设定.md', '3.1-甲.md', '3.8-乙.md', '10-丙.md'):
            (d / name).write_text('# x\n', encoding='utf-8')
        eq(find_episode_md(d, 8).name, '3.8-乙.md', '找脚本：3.8- 命名取集号 8 不是单元号 3')
        eq(find_episode_md(d, 1).name, '3.1-甲.md', '找脚本：3.1- 命名取集号 1')
        eq(find_episode_md(d, 10).name, '10-丙.md', '找脚本：两位数集号')
        eq(find_episode_md(d, 0), None, '找脚本：00- 全片设定不算某一集')


# ---------------------------------------------------------------- 结构锁：不许再有私有解析器
PRIVATE_PARSER_RE = re.compile(r"split\(\s*['\"]## (?:分镜|出图清单)")
OWNERS = ['build_reader.py', 'chapters.py', 'lint_script.py', 'preview_pack.py',
          'retime.py', 'scaffold_episode.py', 'shots_dump.py']


def test_no_private_parsers():
    for name in OWNERS:
        p = SKILL / 'lib' / name
        check(p.exists(), f'结构锁：lib/{name} 存在')
        if not p.exists():
            continue
        src = p.read_text(encoding='utf-8')
        hits = PRIVATE_PARSER_RE.findall(src)
        check(not hits, f'结构锁：lib/{name} 不许再自己切 "## 分镜"/"## 出图清单"',
              f'命中 {len(hits)} 处——解析要走 lib/script_md.py')
        check('script_md' in src, f'结构锁：lib/{name} 应当 import script_md')


# ---------------------------------------------------------------- 真实 9 集：口径自洽
def test_real_corpus_if_present():
    """真实语料在本机才有；没有就跳过（smoke.sh 第 1、2 项已经对它做字节级比对）。"""
    import os
    d = os.environ.get('HDE_SCRIPT_DIR')
    if not d or not Path(d).is_dir():
        return
    mds = [p for p in sorted(Path(d).glob('*.md')) if not p.name.startswith('00-')]
    for p in mds:
        text = p.read_text(encoding='utf-8')
        h, b, t = split_sections(text)
        eq(h + b + t, text, f'真实语料：切分不变式（{p.name}）')
        s = parse(p)
        check(len(s.shots) > 0, f'真实语料：{p.name} 解析出镜头')
        for sh in s.shots:
            check(sh.method in ('程序', '插画'), f'真实语料：{p.name} 镜 {sh.no} 做法合法', sh.method)
        for no, r in s.illus_rows.items():
            check(r.right is not None, f'真实语料：{p.name} 镜 {no} 的 right 不是 None')


def main():
    for fn in [test_roundtrip, test_two_col_table, test_no_illus_section, test_multiline_fields,
               test_odd_headers, test_unknown_field, test_pause, test_no_shots_section,
               test_narration_chars, test_titles, test_find_episode_md,
               test_no_private_parsers, test_real_corpus_if_present]:
        try:
            fn()
        except Exception as e:
            FAILS.append(f'{fn.__name__} 抛异常：{type(e).__name__}: {e}')
    if FAILS:
        print(f'PARSER_DIFF FAIL（{len(FAILS)}/{CHECKS[0]} 条不过）')
        for f in FAILS:
            print(f'  FAIL  {f}')
        return 1
    print(f'PARSER_DIFF OK（{CHECKS[0]} 条断言全过）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
