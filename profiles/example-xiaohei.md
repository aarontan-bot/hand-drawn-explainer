# 预设 · example-xiaohei（最小可跑示例）

这是一个**能跑通的最小预设**，用来演示预设机制、兼作 `evals/smoke.sh` 第 8 项的夹具。
要写自己的预设，从 [_template.md](_template.md) 开始，别改这一份。

## 它演示了什么
`scaffold_episode.py --profile example-xiaohei` 会把同目录 `example-xiaohei/series-defaults.json`
里的字段合并进项目的 `series.json`（只填空字段，你已经填过的不覆盖），于是画风 `xiaohei`
会自动进入生图提示词的风格前缀。把 `series-defaults.json` 里的尖括号占位换成你自己的值即可。

## 一个完整的预设通常还会有
- `example-xiaohei/logo.png`、`ref-style.png`：scaffold 会复制到项目 `assets/`（本示例不带，所以会跳过）
- `example-xiaohei/lint-rules.json`：`lint_script.py` 的额外红线词（受众禁用词、来源泄漏词）
- `example-xiaohei/shot-gallery/`：自己已交付作品的镜头截图 + `index.md`，给 [03-shot-patterns.md](../references/03-shot-patterns.md) 当标尺
- 本文件里写清受众口径、角色设定、音色、目录约定、交付要求

这些都是可选的，缺了不影响内核跑通。
