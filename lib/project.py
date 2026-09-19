"""项目上下文：让脚本自己把参数找齐，而不是等人记得传。

目录约定（见 SKILL.md）：
    <项目根>/
      _chain/            intent / spec / plan
      脚本/              00-全片设定.md  <集号>-<标题>.md
      series.json        标题 / 音色 / 画风 / 角色 / 预设
      第N集/             shots.json  scripts/episode.js  audio/  illus/ …

从集目录往上找 series.json 即可定位项目根。找不到就退化成 None，调用方保留原来的退化逻辑——
本模块只负责「能找到时把参数补上」，不负责改变找不到时的行为。

用法：
    from project import Project
    proj = Project.from_episode_dir(ep_dir)       # 找不到项目根返回 None
    md   = proj.script_for(8) if proj else None
"""
import json
import sys
from pathlib import Path

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB))
import script_md

SERIES_JSON = 'series.json'
SCRIPT_DIRNAME = '脚本'
CHAIN_DIRNAME = '_chain'
MAX_WALK_UP = 8


class Project:
    """一个系列项目的上下文。

    root        项目根（含 series.json 的目录；没有 series.json 时是含「脚本/」的目录）
    series      series.json 的内容（dict；没有该文件时为空 dict）
    profile     series.json 的 profile 字段（没有则 None）
    script_dir  脚本目录（Path；找不到为 None）
    """

    __slots__ = ('root', 'series', 'script_dir')

    def __init__(self, root, series=None):
        self.root = Path(root).resolve()
        if series is None:
            series = _load_series(self.root / SERIES_JSON)
        self.series = series
        self.script_dir = self._resolve_script_dir()

    # ------------------------------------------------------------ 定位
    @classmethod
    def from_series_dir(cls, d):
        d = Path(d).resolve()
        return cls(d) if d.is_dir() else None

    @classmethod
    def from_episode_dir(cls, ep_dir):
        """从集目录往上找项目根（含 series.json 的目录优先，其次含「脚本/」的目录）。"""
        return cls.find(ep_dir)

    @classmethod
    def find(cls, start):
        """从任意路径往上走，找项目根。找不到返回 None。"""
        p = Path(start).resolve()
        if p.is_file():
            p = p.parent
        fallback = None
        for _ in range(MAX_WALK_UP):
            if (p / SERIES_JSON).is_file():
                return cls(p)
            if fallback is None and (p / SCRIPT_DIRNAME).is_dir():
                fallback = p
            if p.parent == p:
                break
            p = p.parent
        return cls(fallback) if fallback else None

    def _resolve_script_dir(self):
        # series.json 里显式写了 script_dir 就用它（相对路径按项目根解析）
        raw = self.series.get('script_dir')
        if raw:
            d = Path(raw)
            d = d if d.is_absolute() else (self.root / d)
            if d.is_dir():
                return d.resolve()
        d = self.root / SCRIPT_DIRNAME
        return d.resolve() if d.is_dir() else None

    # ------------------------------------------------------------ 取件
    def script_for(self, episode_no):
        """该集的脚本 md；找不到返回 None。"""
        if not self.script_dir:
            return None
        return script_md.find_episode_md(self.script_dir, episode_no)

    def lint_rules(self):
        """预设的 lint 规则文件 $HDE/profiles/<profile>/lint-rules.json；没有返回 None。"""
        if not self.profile:
            return None
        p = LIB.parent / 'profiles' / self.profile / 'lint-rules.json'
        return p if p.is_file() else None

    def spec(self):
        """<项目根>/_chain/spec.md；没有返回 None。"""
        p = self.root / CHAIN_DIRNAME / 'spec.md'
        return p if p.is_file() else None

    @property
    def profile(self):
        return self.series.get('profile') or None

    def __repr__(self):
        return f'<Project {self.root.name} profile={self.profile}>'


def _load_series(path):
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        print(f'警告：{path} 不是合法 JSON，按空 series 处理', file=sys.stderr)
        return {}
    return data if isinstance(data, dict) else {}


def episode_no_of(ep_dir):
    """集目录名里的第一段连续数字（第8集 -> 8）；取不到返回 None。"""
    import re
    m = re.search(r'\d+', Path(ep_dir).resolve().name)
    return int(m.group()) if m else None
