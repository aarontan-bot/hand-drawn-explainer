# 第三方组件

本仓库随代码分发以下第三方组件，各自的许可与义务如下。

| 组件 | 版本 | 位置 | 许可 | 许可文件 |
|---|---|---|---|---|
| [rough.js](https://roughjs.com/) | — | `lib/rough.js` | MIT · © 2019 Preet Shihn | `lib/rough-LICENSE.txt` |
| [GSAP](https://gsap.com/) | 3.14.2 | `lib/gsap.min.js` | GSAP Standard "No Charge" License · © 2025 Webflow | 文件头注释 + <https://gsap.com/standard-license> |
| [handraw-style](https://github.com/yang0/handraw-style) | 快照 `6daf50f` | `vendor/handraw-style/` | MIT · © 2026 yang0 | `vendor/handraw-style/LICENSE` |

其中 handraw-style 的 **334 张风格参考图不随本仓库分发**（约 23 MB），由
`vendor/handraw-style/fetch-images.sh` 按需从上游拉取，版本锁在 VENDOR-NOTE 记录的快照。
仓库内只保留它的风格定义、画廊页面与许可文件。

## GSAP 的一点说明

GSAP 自 2025-04-30 起在 Standard License 下**对商业用途免费**，授权明确包含 `use, reproduce,
display, and implement`，所以可以随本仓库分发。两条要注意：

1. **不得移除或修改 `lib/gsap.min.js` 头部的版权与许可注释**（许可条款 III 明确禁止）。
2. 唯一的禁止用途是拿它去做**与 Webflow 竞争的「无需写代码的可视化动画构建器」**。本项目是让
   agent 写 JavaScript 去驱动 GSAP，不属于该情形；条款的 FAQ 也明确 AI 生成 GSAP 代码是允许的。
   如果你在此基础上做出带可视化动画编辑界面的产品，请自行重新评估。

## 运行时依赖（不随仓库分发，需自行安装）

| 依赖 | 用途 | 许可归其各自项目 |
|---|---|---|
| [HyperFrames](https://www.npmjs.com/package/hyperframes) `0.8.20` | 校验与渲染程序动画工程 | 通过 `npx` 按需拉取，版本锁定 |
| FFmpeg（需带 libass） | 合成音视频、烧字幕、抽帧 | 建议 `ffmpeg-full` |
| Google Chrome | 无头截图（自查与量化） | — |
| Python 3 + Pillow、NumPy | 图像处理与量化 | — |
| 任一 TTS 服务 | 配音（`lib/synthesize.py` 当前对接火山引擎，可替换） | 需自备密钥 |
| 任一生图模型（可选） | 插画；走 `illus_mode: svg` 时完全不需要 | 需自备额度 |

## 相关项目

逐笔「边讲边画」路线由另一个开源项目承担，本仓库**不包含它的代码**，只在
[`references/stroke-route.md`](references/stroke-route.md) 里转交：

- [hi-nikola/hand-drawn-explainer-video-nikola](https://github.com/hi-nikola/hand-drawn-explainer-video-nikola)
  — 代码 Apache-2.0，示例素材 CC BY 4.0，提示词 MIT（以该仓库内的许可文件为准）
