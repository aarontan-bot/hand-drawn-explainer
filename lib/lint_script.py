#!/usr/bin/env python3
"""脚本红线扫描 + 制作阶段屏幕文字对账。

脚本模式（默认，检查 脚本/ 下的分镜稿）：
  python3 lint_script.py <脚本目录或单个md> [--rules 额外规则.json ...] [--spec spec.md]
  遍历目录下除 00- 开头外的 *.md（传单个 md 就只查那一个），按镜逐条检查，输出：
  | 严重度 | 文件 | 镜号 | 类型 | 摘录 | 说明 |
  高：镜头头缺做法 / 旁白或屏幕文字命中来源泄漏词或禁用词 / 插画镜不在出图清单里 / 出图描述要求画字。
  中：旁白或屏幕文字命中易变数字模式且不在 --spec 的稳定数字白名单里。
  低：旁白里连写 ≥3 位阿拉伯数字 / 同一英文术语在 ≥2 集的屏幕文字里重复带括号原文。
  末尾汇总高/中/低条数；只要有高，退出码为 1。

制作模式（检查某一集 episode.js 的字面量是否都来自脚本）：
  python3 lint_script.py <脚本目录> --episode-dir <集目录> [--spec spec.md]
  从 <集目录>/scripts/episode.js 抽取全部字符串字面量，与按集号匹配到的脚本 md
  （<脚本目录> 下文件名形如 *.<N>-*.md 或 <N>.*.md）的「屏幕文字」各行、
  「本集卡片」的标题与一句话记住、00-*.md 的贯穿句做子串匹配；
  能在其中任一段落里找到（子串命中）的字面量视为通过，不进报告。

规则文件 lib/lint_rules.json 是内核缺省（通用，不含任何品牌或受众词）；
--rules 可传多个，数组字段与内核规则按值合并去重（预设可以用它加受众红线词）。
白名单：--spec 给的文件里「稳定数字白名单」或「口径锁定」段落中出现的所有数字串（\\d+ 连续数字）。

--rules / --spec 都不给时，从 Project（往上找 series.json）自动补：预设的
profiles/<profile>/lint-rules.json 与项目根的 _chain/spec.md，并在 stderr 说明用了哪些文件。
命令行显式给了就以命令行为准；两者都补不上会明确警告——此前主流程命令两个都不带，
等于白名单判据整个失效，扫出来的 0 条是个假绿灯。
"""
import argparse
import json
import re
import sys
from pathlib import Path

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB))
import script_md
from script_md import find_episode_md
from project import Project

DEFAULT_RULES = json.loads((LIB / 'lint_rules.json').read_text(encoding='utf-8'))

EXCERPT_PAD = 8
EXCERPT_MAX = 60


# ---------------------------------------------------------------- 规则与白名单

def load_rules(extra_paths):
    """内核规则 + --rules 追加；同名数组字段按值合并去重，其余字段直接覆盖。"""
    rules = {k: list(v) for k, v in DEFAULT_RULES.items()}
    for p in extra_paths or []:
        extra = json.loads(Path(p).read_text(encoding='utf-8'))
        for k, v in extra.items():
            if isinstance(v, list):
                merged = list(rules.get(k, []))
                for item in v:
                    if item not in merged:
                        merged.append(item)
                rules[k] = merged
            else:
                rules[k] = v
    return rules


def load_whitelist(spec_path):
    """白名单 = spec.md 里「稳定数字白名单」或「口径锁定」段落中出现的所有数字串。
    没给 --spec 时返回 None（表示不设白名单，全部报）；给了但段落里没有数字返回空集合。"""
    if not spec_path:
        return None
    text = Path(spec_path).read_text(encoding='utf-8')
    m = re.search(r'(?m)^##\s*(?:稳定数字白名单|口径锁定)\s*$(.*?)(?=^##\s|\Z)', text, re.S)
    if not m:
        return set()
    return set(re.findall(r'\d+', m.group(1)))


def digits_whitelisted(matched_text, whitelist):
    if whitelist is None:
        return False
    ds = re.findall(r'\d+', matched_text)
    if not ds:
        return True
    return all(d in whitelist for d in ds)


# ---------------------------------------------------------------- 脚本 md 解析

def excerpt(text, needle=None, pad=EXCERPT_PAD, maxlen=EXCERPT_MAX):
    text = re.sub(r'\s+', ' ', text or '').strip()
    if needle:
        i = text.find(needle)
        if i >= 0:
            text = text[max(0, i - pad):i + len(needle) + pad]
    if len(text) > maxlen:
        text = text[:maxlen] + '…'
    return text


# ---------------------------------------------------------------- 脚本模式规则

def lint_file(path, rules, whitelist):
    sc = script_md.parse(path)
    illus_rows = sc.illus_rows
    fname = path.name
    rows, records = [], []
    for shot in sc.shots:
        no, method = shot.no, shot.method
        nar_raw = shot.narration
        scr_items = shot.screen_items()
        scr_joined = '\n'.join(scr_items)
        records.append((no, method, scr_items))

        if method not in ('插画', '程序'):
            rows.append(('高', fname, no, '缺做法', excerpt(method) or '(空)', '镜头头做法字段必须是「插画」或「程序」'))

        for label, txt in (('旁白', nar_raw), ('屏幕文字', scr_joined)):
            for phrase in list(rules.get('leak_phrases', [])) + list(rules.get('forbidden_phrases', [])):
                if phrase and phrase in txt:
                    rows.append(('高', fname, no, '来源泄漏/禁用词', f'{label}：{excerpt(txt, phrase)}', f'命中「{phrase}」'))
            for pat in rules.get('volatile_number_patterns', []):
                for m in re.finditer(pat, txt):
                    if not digits_whitelisted(m.group(), whitelist):
                        rows.append(('中', fname, no, '数字写死', f'{label}：{excerpt(txt, m.group())}', '不在稳定数字白名单'))

        for m in re.finditer(r'\d{3,}', nar_raw):
            rows.append(('低', fname, no, '数字连写', f'旁白：{excerpt(nar_raw, m.group())}', '建议改成读音顺写法'))

        if method == '插画':
            if no not in illus_rows:
                rows.append(('高', fname, no, '出图清单缺行', f'镜 {no}', '插画镜在出图清单里没有对应行'))
            else:
                # cells 单幅时右是空串不是 None，直接 zip 不会炸
                for side, cell in zip(('左边', '右边'), illus_rows[no].cells):
                    for w in rules.get('illus_text_words', []):
                        if w and w in cell:
                            rows.append(('高', fname, no, '出图要求画字', f'{side}：{excerpt(cell, w)}', f'命中「{w}」，出图描述不能要求画字'))
    return rows, records


TERM_RE = re.compile(r'([\u4e00-\u9fff]{1,10})[（(]([A-Za-z][A-Za-z0-9 .\-]{0,20})[)）]')


def check_term_reuse(file_records):
    """同一英文术语在 ≥2 集的屏幕文字里带括号原文出现，只应首次上屏出现一次。"""
    seen, rows = {}, []
    for fname, records in file_records:
        file_terms = set()
        for no, method, scr_items in records:
            for item in scr_items:
                for zh, en in TERM_RE.findall(item):
                    key = en.strip().lower()
                    if key in file_terms:
                        continue
                    file_terms.add(key)
                    if key in seen and seen[key][0] != fname:
                        rows.append(('低', fname, no, '术语重复上屏', f'{zh}（{en}）', f'{seen[key][0]} 第 {seen[key][1]} 镜已首次上屏，之后应只用中文'))
                    else:
                        seen.setdefault(key, (fname, no))
    return rows


def lint_script_mode(path, rules, whitelist):
    md_files = script_md.iter_script_files(path)
    all_rows, file_records = [], []
    for f in md_files:
        rows, records = lint_file(f, rules, whitelist)
        all_rows.extend(rows)
        file_records.append((f.name, records))
    all_rows.extend(check_term_reuse(file_records))
    return all_rows


# ---------------------------------------------------------------- 制作模式（episode.js 对账）

STR_RE = re.compile(r"'((?:\\.|[^'\\])*)'|\"((?:\\.|[^\"\\])*)\"|`((?:\\.|[^`\\])*)`", re.S)


def html_strip(s):
    s = re.sub(r'<[^>]+>', '', s)
    s = (s.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
         .replace("\\n", '').replace("\\t", '').replace("\\'", "'").replace('\\"', '"'))
    return s.strip()


def js_literals(js_text):
    """去注释后抽取全部字符串/模板字面量；模板串按 ${…} 切开跳过动态部分（不支持嵌套花括号）；
    只留长度 ≥2 且含中文或数字的静态文本，按出现顺序去重。"""
    js_text = re.sub(r'//[^\n]*', '', js_text)
    js_text = re.sub(r'/\*.*?\*/', '', js_text, flags=re.S)
    out = []
    for m in STR_RE.finditer(js_text):
        raw = next(g for g in m.groups() if g is not None)
        for piece in re.split(r'\$\{[^}]*\}', raw):
            piece = html_strip(piece)
            if len(piece) >= 2 and (re.search(r'[\u4e00-\u9fff]', piece) or re.search(r'\d', piece)):
                if piece not in out:
                    out.append(piece)
    return out


def parse_through_sentences(text00):
    idx = text00.find('贯穿三句话')
    if idx < 0:
        idx = text00.find('贯穿句')
        if idx < 0:
            return []
    tail = text00[idx:]
    end = tail.find('\n## ')
    if end > 0:
        tail = tail[:end]
    return [s.strip() for s in re.findall(r'(?m)^\s*\d+\.\s+(.+)$', tail)]


def lint_production(script_dir, episode_dir, whitelist):
    n_m = re.search(r'\d+', episode_dir.name)
    if not n_m:
        print(f'错误：无法从集目录名 {episode_dir.name} 提取集号', file=sys.stderr)
        sys.exit(2)
    n = int(n_m.group())
    ep_md = find_episode_md(script_dir, n)
    if not ep_md:
        print(f'错误：{script_dir} 下找不到匹配第 {n} 集的脚本 md（按文件名第一段连续数字 == {n}）',
              file=sys.stderr)
        sys.exit(2)
    sc = script_md.parse(ep_md)

    allowed = set()
    for shot in sc.shots:
        allowed.update(shot.screen_items())
        for fld in ('旁白', '画面'):   # 2–8 字关键词允许取自旁白；画面说明里点名的标签也算
            v = shot.field(fld)
            if v:
                allowed.add(v)
    if sc.title_short:
        allowed.add(sc.title_short)
    remember = sc.card.get('一句话记住')
    if remember:
        allowed.add(remember)
    for zf in sorted(script_dir.glob('00-*.md')):
        z = zf.read_text(encoding='utf-8')
        allowed.update(parse_through_sentences(z))
        allowed.add(z)   # 全片设定整篇也算允许来源：固定结构表里的提示语（如互动题的暂停提示）来自这里

    js_path = episode_dir / 'scripts/episode.js'
    literals = js_literals(js_path.read_text(encoding='utf-8'))

    # 降噪：cue 事件名、十六进制颜色、不含中文的串不算屏幕文字；比对前统一中英文标点与空白
    cue_names = set()
    shots_json = episode_dir / 'shots.json'
    if shots_json.exists():
        try:
            for d in json.loads(shots_json.read_text(encoding='utf-8')):
                for c in d.get('cues', []):
                    cue_names.add(str(c[0]))
                if 'pause_before' in d:
                    cue_names.add(str(d['pause_before'][0]))
        except Exception:
            pass
    def norm(t):
        t = re.sub(r'\s+', '', t)
        return t.translate(str.maketrans('，。：；！？“”‘’（）', ',.:;!?""\'\'()'))
    allowed_norm = [norm(a) for a in allowed]

    rows = []
    for lit in literals:
        if lit in cue_names or lit.lstrip('#') in cue_names:
            continue
        if re.fullmatch(r'#?[0-9a-fA-F]{3,8}', lit):
            continue
        if not re.search(r'[\u4e00-\u9fff]', lit):
            continue
        ln = norm(lit)
        if any(ln in a for a in allowed_norm):
            continue
        has_digit = bool(re.search(r'\d', lit))
        sev = '中' if has_digit and not digits_whitelisted(lit, whitelist) else '低'
        rows.append((sev, ep_md.name, '-', '制作字面量未对账', excerpt(lit), f'{js_path} 的字面量未在 {ep_md.name} 的屏幕文字/本集卡片/00- 贯穿句里找到子串匹配'))
    return rows, len(literals), len(rows)


# ---------------------------------------------------------------- 输出

SEV_ORDER = {'高': 0, '中': 1, '低': 2}


def print_report(rows):
    rows = sorted(rows, key=lambda r: (SEV_ORDER.get(r[0], 9), r[1], r[2] if isinstance(r[2], int) else 0))
    print('| 严重度 | 文件 | 镜号 | 类型 | 摘录 | 说明 |')
    print('|---|---|---|---|---|---|')
    for sev, fname, no, typ, exc, note in rows:
        print(f'| {sev} | {fname} | {no} | {typ} | {exc} | {note} |')
    counts = {s: sum(1 for r in rows if r[0] == s) for s in ('高', '中', '低')}
    print(f"\n汇总：高 {counts['高']} 条，中 {counts['中']} 条，低 {counts['低']} 条。")


def resolve_inputs(path, args):
    """--rules / --spec 没给时，从 Project 自动补上预设规则与 _chain/spec.md。

    主流程命令 `lint_script.py 脚本/` 两个都不带，白名单判据因此整个失效——
    命中易变数字模式的一律不报、也没有预设的受众红线词，扫出来的 0 条是个假绿灯。
    命令行显式给了就以命令行为准。提示走 stderr（stdout 是报告表格）。"""
    rule_paths = list(args.rules)
    spec_path = args.spec
    if rule_paths and spec_path:
        return rule_paths, spec_path
    proj = Project.find(args.episode_dir or path)
    if not proj:
        if not spec_path:
            print('警告：没给 --spec 且没找到项目根，稳定数字白名单为空（命中易变数字模式的一律报）',
                  file=sys.stderr)
        return rule_paths, spec_path
    if not rule_paths:
        lr = proj.lint_rules()
        if lr:
            rule_paths = [lr]
            print(f'提示：未给 --rules，自动加载预设规则 {lr}', file=sys.stderr)
    if not spec_path:
        sp = proj.spec()
        if sp:
            spec_path = sp
            print(f'提示：未给 --spec，自动用 {sp} 作白名单来源', file=sys.stderr)
        else:
            print(f'警告：{proj.root} 下没有 _chain/spec.md，稳定数字白名单为空', file=sys.stderr)
    return rule_paths, spec_path


def main():
    ap = argparse.ArgumentParser(description='脚本红线扫描 + 制作阶段屏幕文字对账')
    ap.add_argument('path', help='脚本目录或单个 md；制作模式下作为脚本目录用于按集号匹配')
    ap.add_argument('--rules', action='append', default=[], help='额外规则 json，可传多个')
    ap.add_argument('--spec', help='spec.md，取「稳定数字白名单」或「口径锁定」段落作为白名单')
    ap.add_argument('--episode-dir', help='给定则切到制作模式，核对该集 scripts/episode.js')
    args = ap.parse_args()

    path = Path(args.path)
    rule_paths, spec_path = resolve_inputs(path, args)
    rules = load_rules(rule_paths)
    whitelist = load_whitelist(spec_path)

    if args.episode_dir:
        rows, total, unmatched = lint_production(path, Path(args.episode_dir), whitelist)
        print_report(rows)
        print(f'\n字面量共 {total} 条，未对账 {unmatched} 条。', file=sys.stderr)
    else:
        rows = lint_script_mode(path, rules, whitelist)
        print_report(rows)

    sys.exit(1 if any(r[0] == '高' for r in rows) else 0)


if __name__ == '__main__':
    main()
