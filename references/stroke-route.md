# 逐笔"边讲边画"路线（转交）

本 skill 的主路线是"插画 + 线稿程序动画"。用户明确要的是**整幅画面被一笔一笔画出来、笔尖跟着线走、先画左边再画右边并保留前文**时，换用逐笔路线，由另一个开源项目承担：

> **hand-drawn-explainer-video-nikola** — <https://github.com/hi-nikola/hand-drawn-explainer-video-nikola>
> 代码 Apache-2.0，示例素材 CC BY 4.0，提示词 MIT（以该仓库内的 `LICENSE`、`LICENSE-MEDIA.md` 为准）。
> 它带 `vendor/srt-whiteboard-animation/` 白板渲染后端，以及 Q 版人物、xiaohei 风格、双语义岛的规范。

本 skill **不包含**它的任何代码，只在这条路线上把活转交过去；先把那个仓库装到本机，再按下面接。

## 两个项目怎么分工

功能上有重叠——那边也能做程序动画。按**画面怎么动**来分，不按题材分：

- **整幅画面被一笔笔画出来、笔尖跟着线走、先画左边再画右边并保留前文** → 那边
- **镜头逐个切换、图形逐件出现、文字与标注程序层叠加** → 本 skill

## 怎么接

1. 阶段 0–2 仍按本 skill 走（补底、脚本、审稿、关口 ①②）。
2. 阶段 3 改读那个仓库的 `references/stroke-story-workflow.md`。配音仍用本 skill 的 `synthesize.py`，但**交给它的不是逐镜 mp3**，要先转一道，见下。
3. 阶段 4 的终审、交付件、复盘回填仍按本 skill 的 `04-delivery.md`。

## 交接清单（两边的文件粒度不一样，必须转）

| | 本 skill 产出 | 那边期望 |
|---|---|---|
| 音频 | `audio/shot-NN.mp3`，**逐镜 N 个** | `narration.mp3`，**整篇单文件** |
| 节奏依据 | `audio/shot-NN.mp3.json` 词级时间戳 | `captions.srt` |
| 旁白原文 | `audio/shot-NN.txt`，逐镜 | `narration.txt`，整篇 |

好在完整音轨不用自己拼——`build.py` 已经生成了 `comp/assets/narration.wav`，时长与 `timeline.json` 的 `duration` 分毫不差（含片头片尾静音与镜间留白，逐镜 mp3 加起来是不够的）：

```bash
E=第N集                       # 集目录
OUT=/path/to/stroke-work      # 交给那边的工作目录
mkdir -p "$OUT"
ffmpeg -v error -y -i "$E/comp/assets/narration.wav" -codec:a libmp3lame -q:a 2 "$OUT/narration.mp3"
cp "$E/字幕.srt" "$OUT/captions.srt"
for f in "$E"/audio/shot-*.txt; do cat "$f"; echo; done > "$OUT/narration.txt"
```

**前提是先跑过一次 `build.py`**（哪怕 `episode.js` 还是空壳），否则没有 `narration.wav`，也没有 `字幕.srt`。

已知取舍：逐笔路线对"机制讲解"表现力弱（一次实践后用户反馈"怪异、机制解释不清"，改回程序动画）；它适合人物传记、历史故事、单幅大画面的情绪型内容。
