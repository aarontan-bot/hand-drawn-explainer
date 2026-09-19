"""脚本 md 的唯一解析器（格式见 references/02-script.md）。

在此之前 7 个脚本各有一份分镜解析器，口径互不相同，缺口总以同型复发。本模块把这 7 份的能力
取并集，成为唯一真相源；7 个脚本只准从这里取解析结果，不准再自己切 '## 分镜'。

设计口径（逐条都是 7 份实现分歧处的裁决结果）：
- 缺 '## 分镜' 不抛异常：返回空 shots + 警告（原来 scaffold / build_reader / shots_dump 都 IndexError）。
- 缺 '## 出图清单' 不抛异常：tail 为空（原来 retime 在这里 ValueError 崩掉）。
- 字段值支持多行续行，续行遇到任意 `**X**：` 就终止——不设字段名白名单，
  否则未登记字段（如 `**备注**：`）会被静默吞进上一个字段的值里，这种错没人看得见。
- 镜头头容错：段数不足或超出都不抛异常，做法一律取第 3 段，异常时打警告。
- 「停顿」宽松正则 `[\\d.]+\\s*秒`，块内所有匹配求和（一镜可以有多处停顿）；
  但 int/float 的字面形态原样保留，否则 shots.json 的字节会变。
- 出图清单表三列与两列两种写法都认；单幅的「右边」是空串不是 None。
- 旁白字数统一为去标点空白计数（narration_chars）。

所有警告走 stderr：chapters.py 等脚本的 stdout 是交付件内容，不能混进警告。
"""
import re
import sys
from collections import namedtuple
from pathlib import Path

__all__ = [
    'Shot', 'IllusRow', 'Script', 'Sections',
    'parse', 'split_sections', 'split_shot_blocks', 'parse_shots', 'parse_fields',
    'parse_illus_table', 'narration_chars', 'find_episode_md', 'iter_script_files',
]

# 去标点空白后的字数口径（原 retime.py 的 PUNCT，逐字符照搬）
PUNCT_RE = re.compile(r'[\s（）「」《》"“”‘’：、，。？！…—–\-｜·/]')

CIRCLED = '①②③④⑤⑥⑦⑧⑨⑩'

SEP = '｜'

_SEC_SHOTS_RE = re.compile(r'(?m)^##[ \t]*分镜[^\n]*\n?')
_SEC_ILLUS_RE = re.compile(r'(?m)^##[ \t]*出图清单[^\n]*\n?')
_SHOT_SPLIT_RE = re.compile(r'(?m)^### ')
_FIELD_RE = re.compile(r'\*\*(.+?)\*\*[：:](.*)')
_PAUSE_RE = re.compile(r'([\d.]+)\s*秒')
_SILENT_PREFIX = '（无'


def warn(msg):
    """解析层的告警一律走 stderr（stdout 可能是交付件正文）。"""
    print(f'[script_md] {msg}', file=sys.stderr)


# ---------------------------------------------------------------- 字数

def narration_chars(s):
    """旁白字数：去掉标点与空白后的字符数。旁白为「（无…」的镜算 0。

    此前三份实现各不相同：retime.py 去标点空白；preview_pack.py 只去空白（把标点也算成字）；
    第三处压根没数。统一到本函数（去标点空白）。"""
    if not s:
        return 0
    s = s.strip()
    if s.startswith(_SILENT_PREFIX):
        return 0
    return len(PUNCT_RE.sub('', s))


# ---------------------------------------------------------------- 分段

#: (head, body, tail)，满足 head + body + tail == 原文（retime 改写要用这个不变式）。
#: head 含 '## 分镜' 那一行；tail 从 '## 出图清单' 那一行起；缺哪一段对应字段为空串。
Sections = namedtuple('Sections', 'head body tail')


def split_sections(text):
    """切 '## 分镜' 与 '## 出图清单'。两个标记都可以缺，缺了不抛异常。"""
    m1 = _SEC_SHOTS_RE.search(text)
    if not m1:
        return Sections(text, '', '')
    head = text[:m1.end()]
    rest_start = m1.end()
    m2 = _SEC_ILLUS_RE.search(text, rest_start)
    if not m2:
        return Sections(head, text[rest_start:], '')
    return Sections(head, text[rest_start:m2.start()], text[m2.start():])


# ---------------------------------------------------------------- 字段

def parse_fields(block):
    """块内 `**字段**：内容` 逐行解析；不以 `**X**：` 开头的非空行接到上一个字段（多行续行）。

    全角「：」与半角「:」都认。不设字段名白名单：任何 `**X**：` 都终止上一个字段的续行。
    同名字段在一块里重复出现时按出现顺序换行拼接，不是后者覆盖前者——
    一镜可以有多处「停顿」，覆盖就把秒数丢了。"""
    fields, cur = {}, None
    for line in block.split('\n'):
        m = _FIELD_RE.match(line)
        if m:
            cur = m.group(1)
            fields[cur] = (fields[cur] + '\n' + m.group(2)) if cur in fields else m.group(2)
        elif cur and line.strip():
            fields[cur] = (fields[cur] + '\n' + line).strip()
    return fields


def _screen_items(raw, strip_circled=False):
    if not raw:
        return []
    items = []
    for line in raw.split('\n'):
        line = line.strip()
        if not line:
            continue
        # 要求 `- ` 后至少一个空格：这样 "-5 分" 这种负号开头的屏幕文字不会被误剥
        line = re.sub(r'^-\s+', '', line)
        if strip_circled:
            line = line.lstrip(CIRCLED).strip()
        if line:
            items.append(line)
    return items


# ---------------------------------------------------------------- 镜

class Shot:
    """一个分镜块。

    no        镜号（int）
    no_raw    头部第 1 段原文，如 '镜 01'
    span      时间段原文，如 '0:00–0:05'
    method    做法（'程序' / '插画'），取头部第 3 段并 strip；缺失为 ''
    fields    原始字段 dict（值保留多行）
    raw       该镜原文块（不含前导 '### '）
    head      该块首行原文
    head_parts 首行按 '｜' 切开的原始分段（retime 改写要用，保留多余分段）
    """

    __slots__ = ('no', 'no_raw', 'span', 'method', 'fields', 'raw', 'head', 'head_parts')

    def __init__(self, no, no_raw, span, method, fields, raw, head, head_parts):
        self.no = no
        self.no_raw = no_raw
        self.span = span
        self.method = method
        self.fields = fields
        self.raw = raw
        self.head = head
        self.head_parts = head_parts

    def field(self, name, default=None):
        v = self.fields.get(name)
        return default if v is None else v

    @property
    def narration(self):
        return (self.fields.get('旁白') or '').strip()

    @property
    def is_silent(self):
        """旁白为「（无…」——不配音的镜（片头 / 片尾 / 纯画面镜）。"""
        return self.narration.startswith(_SILENT_PREFIX)

    @property
    def narration_chars(self):
        return narration_chars(self.narration)

    def screen_items(self, strip_circled=False):
        """屏幕文字逐条。strip_circled=True 时另去掉行首的 ①②③ 序号。"""
        return _screen_items(self.fields.get('屏幕文字'), strip_circled)

    @property
    def pause_seconds(self):
        """「停顿」秒数：字段内所有 `N 秒` 求和；没有「停顿」字段返回 None。

        int / float 的字面形态原样保留（全是整数就返回 int），shots.json 的字节靠这个不变。"""
        raw = self.fields.get('停顿')
        if not raw:
            return None
        vals = [int(v) if '.' not in v else float(v) for v in _PAUSE_RE.findall(raw)]
        if not vals:
            return None
        return sum(vals)

    @property
    def pause_mid_sentence(self):
        """停顿在旁白中间（省略号后还有话）而不是镜尾——这种不能自动转 pause_end。"""
        return bool(self.fields.get('停顿')) and '…' in self.narration

    def __repr__(self):
        return f'<Shot {self.no:02} {self.method or "?"} {self.span}>'


def split_shot_blocks(body):
    """body -> (前言, [每镜原文块])，满足 前言 + ''.join('### ' + b for b in blocks) == body。

    retime 要按这个不变式把改过头行的块原样拼回去，所以块尾的换行不能 strip 掉。"""
    chunks = _SHOT_SPLIT_RE.split(body)
    return chunks[0], chunks[1:]


def parse_shots(text):
    """解析分镜。传整篇 md 或已经切好的 body 都可以。缺 '## 分镜' 返回 [] 并警告。"""
    if _SEC_SHOTS_RE.search(text):
        body = split_sections(text).body
    elif _SHOT_SPLIT_RE.search(text):
        body = text          # 允许直接传已切好的 body
    else:
        # 只对「看起来就是分镜稿」的文件报警：脚本目录下本来就有 分集建议.md 这类非分镜 md，
        # 对它们每跑一次报一次，只会把人训练成无视警告
        if '**旁白**' in text or '### 镜' in text:
            warn('没有找到 "## 分镜" 段，按 0 镜处理')
        return []
    shots = []
    for blk in split_shot_blocks(body)[1]:
        head = blk.split('\n', 1)[0]
        parts = head.split(SEP)
        no_m = re.search(r'\d+', parts[0])
        if not no_m:
            warn(f'跳过没有镜号的分镜块：{head[:40]!r}')
            continue
        if len(parts) != 3:
            warn(f'镜头头不是 3 段（{len(parts)} 段），做法按第 3 段取：{head[:60]!r}')
        shots.append(Shot(
            no=int(no_m.group()),
            no_raw=parts[0],
            span=parts[1].strip() if len(parts) > 1 else '',
            method=parts[2].strip() if len(parts) > 2 else '',
            fields=parse_fields(blk.split('\n', 1)[1] if '\n' in blk else ''),
            raw=blk,
            head=head,
            head_parts=parts,
        ))
    return shots


# ---------------------------------------------------------------- 出图清单

class IllusRow:
    """出图清单的一行。kind 为 'illus'（左右两幅）或 'single'（单幅，right 为空串）。"""

    __slots__ = ('no', 'kind', 'left', 'right', 'merged_three')

    def __init__(self, no, kind, left, right='', merged_three=False):
        self.no = no
        self.kind = kind
        self.left = left
        self.right = right or ''
        self.merged_three = merged_three

    @property
    def is_single(self):
        return self.kind == 'single'

    @property
    def cells(self):
        """(左, 右) —— 单幅时右是空串。扫描类调用方直接 zip 这个，不会碰到 None。"""
        return (self.left, self.right)

    def __repr__(self):
        return f'<IllusRow {self.no:02} {self.kind}>'


_TWO_COL_HEAD_RE = re.compile(r'^分[两三]层[：:]\s*')
_TWO_COL_THREE_RE = re.compile(r'左层[，,：:](.*?)[；;]\s*中层[，,：:](.*?)[；;]\s*右层[，,：:](.*)$', re.S)
_TWO_COL_SINGLE_RE = re.compile(r'^\*{0,2}单场景居中\*{0,2}[：:]\s*')
# 两列出图清单表里左右分隔的几种写法，按出现顺序试
_TWO_COL_LR_PAIRS = [
    (r'左层[，,]', r'右层[，,]'),
    (r'左层[：:]', r'右层[：:]'),
    (r'左边[：:]', r'右边[：:]'),
    (r'LEFT[：:]', r'RIGHT[：:]'),
]


def strip_single_prefix(desc):
    """'单幅（分三步落墨）：同一只小狐狸…' -> '同一只小狐狸…'（三列表的单幅前缀）"""
    return re.sub(r'^单幅(?:（[^）]*）)?：\s*', '', desc)


def parse_two_col_cell(cell):
    """两列出图清单表（镜号｜画面描述）的单元格 -> (kind, left, right, merged_three)。

    '分两层：左层，X；右层，Y'（也认 左层：/左边：/LEFT： 等写法）-> ('illus', X, Y, False)
    '分三层：左层，X；中层，M；右层，Y' 没有第三岛可放，按 左=X、右=M＋'；'＋Y 合并，
      merged_three=True 提示调用方打印「已把中层并入右岛」
    '单场景居中：Z' 或没有任何标记的整段 -> ('single', Z, '', False)"""
    is_three = bool(re.match(r'^分三层', cell))
    body = _TWO_COL_HEAD_RE.sub('', cell)
    if is_three:
        m = _TWO_COL_THREE_RE.search(body)
        if m:
            left = m.group(1).strip()
            right = m.group(2).strip() + '；' + m.group(3).strip()
            return 'illus', left, right, True
    for lre, rre in _TWO_COL_LR_PAIRS:
        m = re.search(lre + r'(.*?)[；;]\s*' + rre + r'(.*)$', body, re.S)
        if m:
            return 'illus', m.group(1).strip(), m.group(2).strip(), False
    return 'single', _TWO_COL_SINGLE_RE.sub('', cell).strip(), '', False


def parse_illus_table(text):
    """出图清单表 -> {镜号: IllusRow}。两种写法都认：

    三列 | 镜头 | 左边 | 右边 |（右边 '—' 为单幅，左边可能带「单幅：」前缀）
    两列 | 镜号 | 画面描述 |（单元格内用「分两层：左层，…；右层，…」等标记左右，没标记就是单幅）

    表体切到出图清单之后的下一个 '## ' 为止（不写死 '## 知识点对账'：中间夹别的小节时，
    写死的那种切法会把别人的表格行误收进来）。"""
    tail = split_sections(text).tail
    if not tail:
        return {}
    # 去掉 '## 出图清单' 那一行本身，再切到下一个 '## '
    table = _SEC_ILLUS_RE.sub('', tail, count=1).split('\n## ', 1)[0]
    rows = {}
    for line in table.splitlines():
        line = line.strip()
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) < 2 or not re.fullmatch(r'\d+', cells[0]):
            continue
        no = int(cells[0])
        if len(cells) >= 3:
            left, right = cells[1], cells[2]
            if right == '—':
                rows[no] = IllusRow(no, 'single', strip_single_prefix(left))
            else:
                rows[no] = IllusRow(no, 'illus', left, right)
        else:
            kind, left, right, merged = parse_two_col_cell(cells[1])
            rows[no] = IllusRow(no, kind, left, right, merged)
    return rows


# ---------------------------------------------------------------- 整篇

_CARD_ROW_RE = re.compile(r'(?m)^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$')
_DASHES_RE = re.compile(r'^:?-{2,}:?$')
_H1_RE = re.compile(r'(?m)^#\s+(.+)$')


class Script:
    """一份脚本 md 的解析结果。

    title       H1 整行原文（如 '3.8　迭代（下）：怎么改才有效'）
    title_short 砍掉首个 token 后的标题（如 '迭代（下）：怎么改才有效'）——两种语义，各有用处
    card        本集卡片的两列表 {项目: 内容}
    card_keys   卡片字段按首次出现顺序
    shots       list[Shot]
    illus_rows  {镜号: IllusRow}
    head/body/tail  满足 head + body + tail == text
    """

    __slots__ = ('path', 'text', 'title', 'title_short', 'card', 'card_keys',
                 'shots', 'illus_rows', 'head', 'body', 'tail')

    def __init__(self, path, text):
        self.path = Path(path) if path else None
        self.text = text
        sec = split_sections(text)
        self.head, self.body, self.tail = sec.head, sec.body, sec.tail
        self.shots = parse_shots(text)
        self.illus_rows = parse_illus_table(text)
        self.card, self.card_keys = _parse_card(self.head)
        self.title, self.title_short = _parse_title(text)

    def shot(self, no):
        for s in self.shots:
            if s.no == no:
                return s
        return None

    @property
    def shots_by_no(self):
        return {s.no: s for s in self.shots}

    @property
    def name(self):
        return self.path.name if self.path else ''

    def render(self, body=None):
        """按 head + body + tail 拼回整篇（retime 改写用）。"""
        return self.head + (self.body if body is None else body) + self.tail

    def __repr__(self):
        return f'<Script {self.name or "(text)"} {len(self.shots)} 镜>'


def _parse_card(head_text):
    card, keys = {}, []
    for m in _CARD_ROW_RE.finditer(head_text):
        k, v = m.group(1), m.group(2)
        if k in ('项目', '---') or _DASHES_RE.match(k):
            continue
        card[k] = v
        if k not in keys:
            keys.append(k)
    return card, keys


def _parse_title(text):
    m = _H1_RE.search(text)
    if m:
        full = m.group(1).strip()
    else:
        first = text.splitlines()[0] if text.splitlines() else ''
        full = first.lstrip('# ').strip()
    short = re.sub(r'^\S+\s+', '', full)
    return full, short


def parse(path_or_text, path=None):
    """parse(Path | 文件路径字符串 | 整篇正文) -> Script"""
    if isinstance(path_or_text, Path):
        p = path_or_text
        return Script(p, p.read_text(encoding='utf-8'))
    if isinstance(path_or_text, str) and '\n' not in path_or_text and len(path_or_text) < 4096:
        p = Path(path_or_text)
        if p.exists() and p.is_file():
            return Script(p, p.read_text(encoding='utf-8'))
    return Script(path, path_or_text)


# ---------------------------------------------------------------- 找脚本 md

_EP_NUM_RE = re.compile(r'^\D*(\d+(?:\.\d+)*)')


def episode_no_from_name(name):
    """文件名开头的编号 -> 集号。带点的编号（3.8 = 第 3 单元第 8 集）取最后一段。

    原来写成「第一段连续数字」，在 3.8-标题.md 上取到的是单元号 3 而不是集号 8——
    与它自己的文档说明相反，按集号根本找不到文件。"""
    m = _EP_NUM_RE.match(name)
    return int(m.group(1).split('.')[-1]) if m else None


def find_episode_md(script_dir, n):
    """按集号找该集的脚本 md，三种命名都认：01-标题.md / 1-标题.md / 3.8-标题.md。
    00- 开头的全片设定不算某一集。找不到返回 None。"""
    script_dir = Path(script_dir)
    if not script_dir.is_dir():
        return None
    for p in sorted(script_dir.glob('*.md')):
        if p.name.startswith('00-'):
            continue
        if episode_no_from_name(p.name) == int(n):
            return p
    return None


def iter_script_files(path, glob=None):
    """脚本目录 -> 除 00- 开头外的 *.md（按文件名排序）；直接传单个 md 就只返回它。"""
    path = Path(path)
    if path.is_file():
        return [path] if path.suffix == '.md' else []
    if not path.is_dir():
        return []
    if glob:
        return sorted(path.glob(glob))
    return sorted(p for p in path.glob('*.md') if not p.name.startswith('00-'))
