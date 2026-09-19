"""把一份脚本 md（格式见 references/02-script.md）铺成一集的工程骨架。

用法：python3 scaffold_episode.py <脚本md> <集目录> [--series-json <路径>] [--profile <名>] [--illus-mode image|svg]

--profile（或 series.json 里已经填了 profile 字段）：把 profiles/<名>/ 下的 logo.png、
ref-style.png 复制到项目根（系列目录）的 assets/，已存在不覆盖；把 profiles/<名>/series-defaults.json
（speaker/style/illus_mode/characters）合并进 series.json——只填 series.json 里为空或缺失的字段，
用户已填的不覆盖；并把 profile 名写回 series.json。

出图清单表两种格式都认：三列（镜头｜左边｜右边，右边 "—" 为单幅）和两列（镜号｜画面描述，单元格内用
"分两层：左层，…；右层，…"（也认 左层：/右边：/LEFT：/RIGHT： 等写法）拆左右，没有任何标记的整段
就是单幅）。

生成：
  audio/shot-NN.txt        旁白原文（旁白为"（无…"的镜不生成）
  shots.json                骨架：title/end 自动；插画镜按出图清单表分 illus/single；
                             程序镜 kind 留占位 "<填构建器名>" 待人工填；「停顿」在镜尾（旁白到此为止）
                             自动转成 pause_end，旁白中间的停顿（省略号后还有话）留给人工填 pause_before
  illus_mode（缺省 image，取值优先级 --illus-mode > series.json 的 illus_mode 字段）：
    image（缺省，行为不变）→ illus/rows.json {"NN":[左边,右边]}（单幅为 [描述]）+ illus/生图提示词.md
    svg  → 插画镜不出图，改在程序层直接画场景：shots.json 里该镜写 kind:"scene"，cues 是
           [["left",…],["right",…]]（单幅是 [["main",…]]）；改生成 illus/场景说明.md（画面描述原文
           + 四行待填：画布分区/大块区域与遮挡顺序/对象清单/共用坐标），不生成 rows.json 与生图提示词.md
已存在的文件不覆盖，只打印跳过。完成后在系列目录的 进度.md 里记一笔「脚手架」。
"""
import argparse, datetime, json, shutil, sys
from pathlib import Path

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB))
import progress
import script_md

STYLE_PREFIXES = {
    # 内核缺省画风：不带任何项目专属角色/口径的通用线稿风
    'line': "Clean hand-drawn line illustration, 16:9 landscape, white paper background, "
            "sparse slightly wobbly black ink lines, large clean negative space, flat shapes, "
            "only a few small accent colors on objects.",
    # 可选画风（按预设选用，不是内核缺省）
    'xiaohei': "Minimalist hand-drawn editorial illustration, 16:9 landscape, pure white background, "
               "sparse slightly wobbly black ink lines, large clean negative space, flat shapes, "
               "only small red / orange / blue accents and light flat color on objects.",
}
# style / illus_mode 必须留空：apply_profile 只在字段为空时才合并预设值，预填内核缺省等于把预设的
# 画风与出图路径永久挡在门外（真正的缺省在使用点兜底：build_prompt_doc 的 series.get('style') or 'line'）
DEFAULT_SERIES = {"title": "", "speaker": "", "style": "", "characters": "", "profile": "", "illus_mode": ""}


def classify(shots, table):
    """返回 {no: 'title'|'end'|'illus'|'single'|'program'}，以及 illus/single 的画面描述 {no:(left,right,kind)}

    插画镜在出图清单里缺行时打印警告再降级成单幅空描述——以前是静默降级，
    只有另跑一次 lint_script.py 才报，实际上没人会为这个专门跑一次。"""
    kinds, illus_info = {}, {}
    n = len(shots)
    for i, s in enumerate(shots):
        no = s.no
        if i == 0:
            kinds[no] = 'title'
        elif i == n - 1:
            kinds[no] = 'end'
        elif s.method == '插画':
            row = table.get(no)
            if row is None:
                print(f'警告：镜 {no:02} 是插画镜，但出图清单里没有对应行——'
                      f'本次降级成单幅空描述，请补上清单再重跑', file=sys.stderr)
                kind_, left, right = 'single', '', ''
            else:
                kind_, left, right = row.kind, row.left, row.right
                if row.merged_three:
                    print(f'镜 {no:02} 原文分三层，已把中层并入右岛，请人工核对')
            kinds[no] = kind_
            illus_info[no] = (left, right, kind_)
        else:
            kinds[no] = 'program'
    return kinds, illus_info


def build_shots_json(shots, kinds, illus_mode='image'):
    lines = []
    for s in shots:
        no = s.no; kind = kinds[no]
        if kind == 'title':
            d = {'no': no, 'kind': 'title', 'fixed': 5.0}
        elif kind == 'end':
            d = {'no': no, 'kind': 'end', 'fixed': 3.0}
        elif kind == 'illus' and illus_mode == 'svg':
            d = {'no': no, 'kind': 'scene', 'cues': [['left', '<填左半幅开始画的旁白短语>'], ['right', '<填右半幅开始画的旁白短语>']]}
        elif kind == 'single' and illus_mode == 'svg':
            d = {'no': no, 'kind': 'scene', 'cues': [['main', '<填开始画的旁白短语>']]}
        elif kind == 'illus':
            d = {'no': no, 'kind': 'illus', 'cues': [['right', '<填右半幅揭开时的旁白短语>']]}
        elif kind == 'single':
            d = {'no': no, 'kind': 'single', 'cues': []}
        else:
            d = {'no': no, 'kind': '<填构建器名>', 'cues': []}
        # 「停顿」只有在旁白到此为止时才能自动转 pause_end；旁白里出现省略号（……）说明暂停后
        # 同一镜还有话要接着说，那是 pause_before（挂在哪个 cue 键上是人工决定的事），脚手架不猜。
        mid_sentence = s.pause_mid_sentence
        pause = None if mid_sentence else s.pause_seconds
        if pause is not None and kind not in ('title', 'end'):
            d['pause_end'] = pause
        if mid_sentence:
            print(f'提示：镜 {no:02} 的「停顿」在旁白中间（省略号后还有话），不是镜尾——'
                  f'请在 episode.js 写好 cue 后手动加 "pause_before": ["事件名", 秒数]，脚手架不猜这个。')
        lines.append(json.dumps(d, ensure_ascii=False))
    return '[\n' + ',\n'.join(' ' + l for l in lines) + '\n]\n'


def load_or_init_series(path):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            print(f'警告：{path} 不是合法 JSON，本次按缺省 series.json 处理（不覆盖原文件）')
            return dict(DEFAULT_SERIES)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(DEFAULT_SERIES, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'提示：未找到 {path}，已创建缺省 series.json，请手动填写 title/speaker/style/characters/profile')
    return dict(DEFAULT_SERIES)


def apply_profile(series, profile_name, episode_dir):
    """把 profiles/<名>/ 下的 logo.png、ref-style.png 复制到系列目录 assets/（已存在不覆盖）；
    把 profiles/<名>/series-defaults.json（speaker/style/illus_mode/characters）合并进 series.json——
    只填 series.json 里为空或缺失的字段，用户已经填过的不覆盖；并把 profile 名记进 series dict
    （落不落盘由调用方决定）。"""
    profile_dir = LIB.parent / 'profiles' / profile_name
    if not profile_dir.exists():
        print(f'警告：找不到 {profile_dir}，跳过取资产')
        return
    assets_dir = episode_dir.parent / 'assets'
    for fname in ('logo.png', 'ref-style.png'):
        src = profile_dir / fname
        if not src.exists():
            continue
        dst = assets_dir / fname
        if dst.exists():
            print(f'跳过（已存在）：{dst}')
            continue
        assets_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f'写入 {dst}（来自 profiles/{profile_name}/）')
    defaults_path = profile_dir / 'series-defaults.json'
    if defaults_path.exists():
        try:
            defaults = json.loads(defaults_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            print(f'警告：{defaults_path} 不是合法 JSON，跳过合并缺省值')
            defaults = {}
        for k, v in defaults.items():
            if not series.get(k):
                series[k] = v
                print(f'从 profiles/{profile_name}/series-defaults.json 补上 series.json 的 {k} = {v!r}')
    series['profile'] = profile_name


def build_prompt_doc(series, episode_dir, illus_info):
    style = series.get('style') or 'line'
    lines = ['# 生图提示词', '', '## 所有图共用的要求', '']
    if style in STYLE_PREFIXES:
        lines.append(f'- 风格：{STYLE_PREFIXES[style]}')
    else:
        lines.append(f'- 风格：{style}')
        lines.append('- 按 series.json 的 style 补风格前缀')
    lines.append('- 构图：16:9；左上角与右上角留空；底部 18% 留空；左右岛中间留 8% 的沟；'
                 '绝对不出现任何文字、数字、伪字、logo、水印；不画圈、框、箭头、问号。')
    if series.get('characters'):
        lines.append(f'- 角色设定：{series["characters"]}')
    if (episode_dir.parent / 'assets/ref-style.png').exists():
        lines.append('- 参考图见 assets/ref-style.png')
    lines += ['', '## 分镜画面', '', '| 文件 | 画面 |', '|---|---|']
    for no in sorted(illus_info):
        left, right, kind = illus_info[no]
        fname = f'{no:02}.png'
        desc = f'单场景居中：{left}' if kind == 'single' else f'LEFT：{left} RIGHT：{right}'
        lines.append(f'| {fname} | {desc} |')
    return '\n'.join(lines) + '\n'


def build_scene_doc(illus_info):
    """svg 画法（程序层直接画场景，不出图）时代替 rows.json + 生图提示词.md 的说明文档：
    每个插画镜一段，画面描述原文照抄，四行留给人工填。"""
    lines = ['# 场景说明（svg 画法）', '']
    for no in sorted(illus_info):
        left, right, kind = illus_info[no]
        lines.append(f'### 镜 {no:02}')
        lines.append('')
        if kind == 'single':
            lines.append(f'- 单幅：{left}')
        else:
            lines.append(f'- 左边：{left}')
            lines.append(f'- 右边：{right}')
        lines += ['', '画布分区：', '大块区域与遮挡顺序：', '对象清单（从大到小）：', '共用坐标：', '']
    return '\n'.join(lines).rstrip() + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('script_md')
    ap.add_argument('episode_dir')
    ap.add_argument('--series-json', default=None)
    ap.add_argument('--profile', default=None)
    ap.add_argument('--illus-mode', default=None, choices=['image', 'svg'])
    args = ap.parse_args()

    md_path = Path(args.script_md).resolve()
    episode_dir = Path(args.episode_dir).resolve()

    sc = script_md.parse(md_path)
    shots = sc.shots
    if not shots:
        raise SystemExit(f'错误：{md_path} 里没有解析出分镜（缺「## 分镜」段？）')
    kinds, illus_info = classify(shots, sc.illus_rows)

    audio_dir = episode_dir / 'audio'; illus_dir = episode_dir / 'illus'
    audio_dir.mkdir(parents=True, exist_ok=True); illus_dir.mkdir(parents=True, exist_ok=True)

    series_path = Path(args.series_json).resolve() if args.series_json else episode_dir.parent / 'series.json'
    series = load_or_init_series(series_path)
    profile_name = args.profile or series.get('profile') or None
    if profile_name:
        before = json.dumps(series, ensure_ascii=False, sort_keys=True)
        apply_profile(series, profile_name, episode_dir)
        if json.dumps(series, ensure_ascii=False, sort_keys=True) != before:
            series_path.write_text(json.dumps(series, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            print(f'已写回 {series_path}（profile 及合并进来的缺省字段）')
    # illus_mode 要在 profile 合并（可能带来 series.json 的 illus_mode 缺省值）之后再算
    illus_mode = args.illus_mode or series.get('illus_mode') or 'image'

    # 1) audio/shot-NN.txt
    for s in shots:
        if s.is_silent:
            continue
        nar = s.narration
        p = audio_dir / f'shot-{s.no:02}.txt'
        if p.exists():
            print(f'跳过（已存在）：{p}')
            continue
        p.write_text(nar, encoding='utf-8')
        print(f'写入 {p}')

    # 2) shots.json
    shots_json_path = episode_dir / 'shots.json'
    if shots_json_path.exists():
        print(f'跳过（已存在）：{shots_json_path}')
    else:
        shots_json_path.write_text(build_shots_json(shots, kinds, illus_mode), encoding='utf-8')
        print(f'写入 {shots_json_path}')

    if illus_mode == 'svg':
        # svg 画法：插画镜直接在程序层画场景，不出图，不生成 rows.json / 生图提示词.md
        scene_path = illus_dir / '场景说明.md'
        if scene_path.exists():
            print(f'跳过（已存在）：{scene_path}')
        else:
            scene_path.write_text(build_scene_doc(illus_info), encoding='utf-8')
            print(f'写入 {scene_path}')
    else:
        # 3) illus/rows.json
        rows_path = illus_dir / 'rows.json'
        if rows_path.exists():
            print(f'跳过（已存在）：{rows_path}')
        else:
            rows = {}
            for no in sorted(illus_info):
                left, right, kind = illus_info[no]
                rows[f'{no:02}'] = [left] if kind == 'single' else [left, right]
            rows_path.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            print(f'写入 {rows_path}')

        # 4) illus/生图提示词.md
        prompt_path = illus_dir / '生图提示词.md'
        if prompt_path.exists():
            print(f'跳过（已存在）：{prompt_path}')
        else:
            prompt_path.write_text(build_prompt_doc(series, episode_dir, illus_info), encoding='utf-8')
            print(f'写入 {prompt_path}')

    progress.update(episode_dir.parent, episode_dir.name, '脚手架', f'✅ {datetime.date.today().isoformat()}')


if __name__ == '__main__':
    main()
