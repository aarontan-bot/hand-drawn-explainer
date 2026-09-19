# 阶段 3 · 制作：每集工程（配音 → 插画 → 程序动画 → check）

主循环负责：规范、第 1 集样片（关口 ③）、派单、终审、渲染。**子代理负责一集**：shots.json + episode.js + marks.json + build + check + 截图自查，**不渲染 mp4、不写交付目录**。插画走 [03-illustration.md](03-illustration.md)，可与程序动画并行。

## 0. 一集的顺序
```
python3 $HDE/lib/scaffold_episode.py 脚本/<集>.md 第N集 [--profile <预设名>]   # 骨架：audio/shot-NN.txt、shots.json、illus/rows.json、illus/生图提示词.md；用预设的项目必须带 --profile（复制 Logo 与参考图、合并音色画风缺省）
python3 $HDE/lib/synthesize.py 第N集                          # 配音，逐镜缓存，合成后立刻做截断校验
（插画按 03-illustration 出图，放回 第N集/illus/NN.png）
写 第N集/scripts/episode.js，补全 shots.json 的 kind 与 cues
python3 $HDE/lib/build.py 第N集                               # comp/ timeline.json 字幕.srt
cd 第N集 && npx hyperframes@0.8.20 check comp                 # 必须 0 error
截图自查 + python3 $HDE/lib/shot_metrics.py 第N集              # 见 §4
```
集目录：`audio/`（shot-NN.mp3 + .mp3.json 词级时间戳 + shot-NN.txt 旁白，唯一真相源）、`illus/`（NN.png + rows.json + marks.json）、`scripts/episode.js`、`shots.json`、`comp/`、`timeline.json`、`字幕.srt`。快速看分镜：`python3 $HDE/lib/shots_dump.py 脚本/<集>.md`。

## 1. shots.json
数组，每镜 `{"no":镜号,"kind":"构建器名","cues":[["事件名","旁白触发短语"],...]}`。
- 第 1 镜固定 `{"no":1,"kind":"title","fixed":5.0}`；末镜 `{"no":N,"kind":"end","fixed":3.0}`。
- 插画镜 `kind:"illus"`，至少一个 `["right","…"]`（右半幅揭开的时机）；单幅图 `kind:"single"`，无 cues。
- 需要停顿的镜加 `"pause_end": 秒数`（按脚本「停顿」）；句中停顿用 `"pause_before": ["事件名", 秒数]`。
- **触发短语必须逐字取自 `audio/shot-NN.txt`，按出现顺序排列**：build.py 去掉标点空格后顺序查找，短语要能唯一定位。事件名随意，但要和 episode.js 的 `sc.at('名')` 一一对应，缺一个就报错。

## 2. episode.js
```js
const EP={no:N,title:'…',sub:'…'};          // 片头
// 本集独有的画法 helper 写在这里，不改 core.js
Object.assign(BUILD,{ 构建器名(sc,s){ … }, … });
```
`core.js`（`$HDE/lib/core.js`）已提供（下面点名的 helper 由 `evals/smoke.sh` 第 7 项逐个核对存在）：
- **时间**：`sc.t0` `sc.t1`；`sc.at('事件名'[,偏移])`。
- **入场**：`sc.draw(节点,t,时长)` 线条逐笔画出（首选）、`sc.pop` 弹入（小元素）、`sc.fade(节点,t)`、`sc.out(节点,t)`。
- **手绘图形**（rough.js，固定种子）：`line rect circle ellipse path rrect arrow(d,x2,y2,角度)`，opt `{stroke,strokeWidth,fill,fillStyle:'solid'}`。
- **道具**：`phone paper bubble cloud stamp check cross hourglass`；**预设角色 helper**：`xiaohei robot`（只在预设或全片设定定义了该角色时用，通用版不用）。
- **图标** `sc.icon(kind,x,y,scale)`，kind 清单见 [03-shot-patterns.md](03-shot-patterns.md) 末节。
- **纸条** `sc.note(x,y,w,html,t,{size,weight,tag,tagColor,lh})` → `{el,h}`；配 `sc.mark(span,t)` 高亮扫过、`sc.ringSpan(span,t)` 红圈、`sc.strikeSpan(span,t)` 划掉。
- **停顿沙漏** `sc.hourglassPause(s,x,y)`；**结尾金句** `sc.remember(一句话, 贯穿句, 时刻one, 时刻thru, [...sc.svg.children])`。
- **文字** `sc.text(x,y,str,{size,weight,color,anchor})`（单行）；`sc.html(x,y,w,inner,cls,style)`（会换行）。
- 内置构建器 `title illus single end`，不用自己写。

## 3. 视觉口径（ELI5 线稿风；违反要返工）

「ELI5 线稿风」= 像给完全不懂的人讲那样：**一屏一个意思、图大字少、全部手绘墨线**。下面九条是它的可操作版本，再下面的表格是机器能量的判据。
1. **大图少字**：一屏一个意思；文字是标签不是段落。禁止 UI 卡片列表（圆角卡片堆 + 小字项目符号）、阴影、渐变、灰色小标签。
2. **每镜一个主图**：脚本「画面」栏写的主图必须是屏上最大的东西，高度不小于安全区的三分之一；部件围着它摆，部件不超过 6 个。
3. 全部手绘墨线（rough.js），和插画同一支笔。字体苹方，正文 ≥40px，标题 60–90px。
4. 画布 1920×1080。**安全区 y ∈ [130, 860]**（这是全 skill 唯一的安全区数字，`shot_metrics.py` 按它判）：y < 130 是 Logo / 集数条，y > 860 留给字幕条（字幕条本体从 886 起，860–886 是缓冲），插画底部约 18% 留空对应的就是这一段。
5. 颜色两层：墨黑打底，彩色只用来指出重点，**一屏最多两种彩色**（机器量）；每种颜色的含义只写在 `00-全片设定.md` 的颜色表里并跨集锁定，这里不重复。
6. 每集一个**贯穿视觉隐喻**（一把伞的几根骨、一个画框的几格、一排工具），讲解镜、答题镜、总结镜复用同一套图形。
7. 元素不压字：文字基线和方框边线至少留 20px。
8. **每个事件都要有动作**：不许一屏内容一次性全出现；讲解镜靠逐件出现和高亮推进，整屏完全不动的时间不超过 13 秒（`motion_check.py` 量，阈值取自已交付九集的 P90）。
9. 镜头怎么画先查 [03-shot-patterns.md](03-shot-patterns.md)：按"画面关系"选模式，并读该模式指向的源码。

### 量化判据（`shot_metrics.py` 与 `motion_check.py`；阈值来源见文末基线）
| 量 | 判据 | 严重度 |
|---|---|---|
| 每镜「画完」时屏上字数 | > 65（提示词工程 9 集 P90，2026-09-18） | 中 |
| 最小字号（不含纸条标签角标） | < 40px | 中 |
| 安全区出界元素（插画整幅出血不计） | 任何 | 高 |
| 最大图形高度 | < 安全区高 1/3 | 低（主图不够大） |
| 一屏彩色数 | > 2 | 低 |
| 静止段（成片复测） | 最长 > 13 s 或占比 > 0.95（提示词工程 9 集 P90，2026-09-18） | 低（提示：320×180 抽样测不到小元素的动作，以抓帧目视为准） |

## 4. 构建与自查
```bash
python3 $HDE/lib/build.py 第N集
cd 第N集 && npx hyperframes@0.8.20 check comp        # 0 error
# 每镜"画完"时刻
python3 -c "
import json;d=json.load(open('第N集/timeline.json'))
print(' '.join(str(round(min(s['end']-0.5,(max(s['events'].values())+1.8) if s['events'] else s['start']+2.5),2)) for s in d['scenes']))"
E=$PWD/第N集; zsh $HDE/lib/peek.sh $E /tmp/pN_a.png 时刻1 时刻2 时刻3 时刻4     # 四张一组，E 必须绝对路径
python3 $HDE/lib/shot_metrics.py 第N集                # 逐镜读数与标记
```
用 Read 工具真的看每张截图：压字、出安全区、图形画歪、留白太空、文字太多。发现问题改 episode.js 重来，直到每屏干净、metrics 无高中项。

## 5. marks.json（插画镜）
`illus/marks.json`：`{"02":{"split":0.45},"10":{"split":0.5,"box":[x,y,w,h,"#D9483B"]}}`。`split` 是左右两幅分界比例，按 rows.json 里左右内容实际占比调；`box/ring/q/arrow` 是程序层叠在图上的标注，需要 cue 名 `mark`。坐标没把握就先不加，留给主循环。

## 6. 派单与看门狗（主循环）
- 关口 ③ 过了才派其余各集；每集一个子代理，**4 个一波**，一波完成并释放后再派下一波（派前看全机占用）。
- 子代理硬边界：只写自己的集目录；不渲染 mp4；不写交付目录；不改 core.js（要改的写进交回报告）。
- 要求**边做边写盘**（每完成两三镜就 build 一次），交回格式：集号、时长、check 结果、贯穿隐喻是什么、metrics 读数、拿不准的地方。
- 报告要抽验：随机看它两张截图；也别急着断定它错，先把证据看全。
- 子代理报"规范 / 脚本本身有错"最值钱：一句话裁定，能推广的写回全片设定或本文档。
- 并行共享脚本的临时文件都带进程号（peek.sh 已带），别用固定名。

## 7. 改稿怎么做（cue 是短语不是帧号，所以便宜）
- 改旁白：改 `audio/shot-NN.txt` → 删该镜的 mp3 与 mp3.json → `synthesize.py 第N集` 只重合成这一镜 → `build.py`。cues 若引用了改掉的短语，同步改 shots.json。
- 改画面：只改 episode.js → `build.py`。配音、插画、其它镜全部不动。
- 改插画：换 `illus/NN.png` → `build.py`（会重新复制到 comp/assets）。

## 8. 探针
新系列第一次派单前，主循环先跑 `zsh $HDE/lib/probe/probe.sh /tmp/probe-overview.png`（用 build.py 构建 `lib/probe/` 探针集，截出 core.js 全部图标、角色、纸条、金句的总览图），用 Read 看图确认共用层渲染正常，再派子代理。core.js 有改动也先跑它。

## 基线
上表阈值取自已交付的提示词工程 9 集（203 镜）分布的 P90（2026-09-18）：屏上字数 P50 24 / P90 65；最小字号 P50 38 / P90 46；主图高 P50 377；彩色数 P50 1 / P90 3；静止占比 P50 0.90 / P90 0.95；最长静止 P50 7.0 s / P90 12.8 s。重算：`shot_metrics.py --baseline <系列目录>` 与 `motion_check.py --baseline <系列目录>`；换阈值时改本表、`lib/metrics_thresholds.json` 与 `motion_check.py` 默认值并注明日期。
