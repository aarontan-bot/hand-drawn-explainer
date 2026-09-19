---
name: hand-drawn-explainer
description: 把一个概念、一份知识稿或一份现成文稿做成手绘讲解视频（配音 + 字幕 + 插画 + 线稿程序动画 + 真实 MP4），五阶段推进，四个关口等用户拍板。用户说"做一条讲 X 的视频""把这份稿子 / 课程模块做成视频""脚本化""做第 N 集""补插画""渲染成片"时用；只要"边讲边画、一笔笔画出来"的逐笔路线时按 references/stroke-route.md 转交。
---

# 手绘讲解视频

一个入口走到成片。内核对任何主题、受众、画风都成立；受众口径、固定角色、品牌、音色、目录这些按**预设**（`profiles/`）加载，不选预设就是通用版。

下文 `$HDE` = 本 skill 根目录（`~/.claude/skills/hand-drawn-explainer`），脚本都在 `$HDE/lib/`。

## 开工先定三件事
1. **输入类型**：概念（一句话主题）/ 知识稿（知识点、例子、术语齐全）/ 现成文稿（文章、转录、旧脚本）。决定要不要走阶段 1。
2. **预设**：问一句"用哪个预设"，列出 `profiles/` 下的文件名；不选 = 通用版。选定后先读该预设，它覆盖内核的缺省值。
3. **交付范围**：单集短片 / 系列 / 只做某一阶段（"补第 3 集插画""重渲第 5 集"）。只做某阶段时从该阶段文档进入，复用已有产物。

然后读 [00-intake.md](references/00-intake.md)：四问、成本预估、落 `_chain/`。

## 五阶段
| 阶段 | 读 | 产出 | 关口 |
|---|---|---|---|
| 0 入口 | [00-intake.md](references/00-intake.md) | `_chain/`、`series.json`、成本预估 | 四问答案 |
| 1 补底（概念 / 现成文稿才做） | [01-grounding.md](references/01-grounding.md) | `_grounding/知识底座稿.md` | ① 用户确认底座稿 |
| 2 脚本 | [02-script.md](references/02-script.md) | `脚本/00-全片设定.md`、每集脚本、`脚本审阅版.html` | ② 逐集确认 |
| 3 制作 | [03-production.md](references/03-production.md) → [03-illustration.md](references/03-illustration.md) | `第N集/{audio,illus,scripts,comp}` + check 通过 | ③ 第 1 集样片 |
| 4 交付 | [04-delivery.md](references/04-delivery.md) | 成片、字幕、封面、章节、README | ④ 全集 |

关口是硬的：没过就不往下派活；关口之间不再问用户。

## 跨阶段铁律
- **时间只来自真实音频**：镜头起止、字幕、事件时刻全部由配音的词时间戳生成，脚本里的时间段只是估算。
- **屏幕上的每个字都来自脚本的「屏幕文字」栏**，一字不差；生图模型不写任何字，文字、圈框、箭头、问号全部程序层叠加。
- **改词只重做那一镜**：cue 是旁白短语不是帧号，改哪一镜就只重合成哪一镜，时间轴自动重算。
- **事实以底座稿 / 知识稿为准**：脚本与它的差异记「需回写清单」，不悄悄改真相源。
- **系列结束做复盘回填**（04-delivery 末节）：新坑进 [gotchas.md](references/gotchas.md) 并当场改对应脚本。

## 目录约定（项目内相对结构；绝对位置按预设）
```
<项目根>/
  _chain/            intent / spec / plan
  _grounding/        知识底座稿（阶段 1）
  脚本/              00-全片设定.md  <集号>-<标题>.md  分集建议.md  脚本审阅版.html
  series.json        标题 / 音色 / 画风 / 角色 / 预设
  assets/            logo.png（可选）  ref-style.png（可选）
  第N集/             shots.json  scripts/episode.js  audio/  illus/  comp/  render/  reports/
  进度.md            集 × 阶段，脚本自动更新
  交付/              成片  字幕  封面  章节  README（预设可指到别处）
```

## 工具一览（`$HDE/lib/`）
`scaffold_episode.py` 脚本 md → 集目录骨架 ｜ `shots_dump.py` 快速看脚本 md 的分镜 ｜ `synthesize.py` 配音 + 截断校验 ｜ `build.py` 时间轴 / 字幕 / 工程 ｜ `peek.sh` 定时截图 ｜ `probe/probe.sh` core.js 共用层探针总览图 ｜ `shot_metrics.py` 每镜量化 ｜ `lint_script.py` 红线与对账 ｜ `retime.py` 脚本时间码估算 ｜ `build_reader.py` 审阅版 ｜ `move_dl.sh` 网页生图下载归位 ｜ `review.py` 成片逐镜抓帧 ｜ `filmstrip.py` 成片密集抽帧看动作过程 ｜ `motion_check.py` 静止段 ｜ `cover.py` `chapters.py` `preview_pack.py` 交付件 ｜ `doctor.sh` 环境预检 ｜ `progress.py` 进度表。回归：`$HDE/evals/smoke.sh`。

任何报错先查 [gotchas.md](references/gotchas.md)。镜头怎么画按 [03-shot-patterns.md](references/03-shot-patterns.md) 选模式。
