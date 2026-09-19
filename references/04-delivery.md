# 阶段 4 · 交付：渲染 → 终审 → 交付件 → 复盘回填

**管这一段**：把 check 通过的每集工程变成验收过的成片，落到交付区，并把这一轮学到的写回 skill。产出：`render/*.mp4`、终审表、交付件、README、回填后的 gotchas / 模式表。

## 1. 渲染（主循环）
```bash
zsh $HDE/lib/doctor.sh                          # ffmpeg(libass)、node、hyperframes 版本、Pillow、Chrome、TTS 密钥、磁盘余量
cd 第N集 && mkdir -p render reports
PRODUCER_STREAMING_ENCODE_MAX_DURATION_SECONDS=1200 \
nohup npx hyperframes@0.8.20 render comp -o render/第N集_v1.mp4 > reports/render.log 2>&1 &
python3 $HDE/lib/progress.py .. 第N集 渲染 "✅ v1 <时长>"      # 渲完记一笔
```
> 进度表 8 列里只有「脚手架 / 配音 / 程序动画」三列由脚本自动写，**渲染 / 终审 / 交付这三列靠下面各命令块末尾的 `progress.py` 串上**，插画与 check 仍要人工补（`progress.py <系列目录> <集号> <阶段> <状态>`）。
- 版本锁 `hyperframes@0.8.20`；流式编码环境变量必须带，否则长片退回磁盘帧捕获，索要几十 GB 临时空间。
- 长渲染必须 `nohup … &` 脱离会话；`--low-memory-mode` 不是流式开关。
- 渲完核对：`ffprobe` 能完整解码、时长 = timeline.json 的 duration、有音轨、最后 0.5 秒不是黑帧。
- 版本号 v1 / v2 递增，不覆盖。

## 2. 终审（主循环亲自看）
```bash
python3 $HDE/lib/review.py 第N集 第N集/render/第N集_v1.mp4 /tmp/rvN     # 每镜一帧拼 9 宫格
python3 $HDE/lib/filmstrip.py 第N集/render/第N集_v1.mp4 /tmp/fsN         # 每 2.4 秒一帧，看动作过程
python3 $HDE/lib/motion_check.py 第N集/render/第N集_v1.mp4 第N集/timeline.json
python3 $HDE/lib/shot_metrics.py 第N集
python3 $HDE/lib/progress.py . 第N集 终审 "✅ 高0中0低N"        # 终审结论记一笔
```
**两张都要看，它们看的不是同一件事**：`review.py` 的 9 宫格看「每镜画完对不对」，`filmstrip.py` 的联系表看「过程中有没有打架」。只在动画中途出现的错误——元素落在半路、两个 tween 抢同一个属性、opacity 被后画的元素盖回去——到「画完时刻」已经复原，9 宫格和 `shot_metrics` 结构上都看不见（2026-09-18 的测试片就这样漏过一个 dim 失效，终审全绿）。

用 Read 逐张看：压字、出界、图形画歪、留白太空、文字太多、插画与程序层跳色、字幕压主体；联系表另看节拍是否有空窗、入场中间态是否难看。
问题记成表，一镜一行，没问题也写 OK：

| 严重度（高/中/低） | 集 | 镜 | 时刻 | 现象 | 判据 | 建议修法 |
|---|---|---|---|---|---|---|

高 = 文字不可读 / 遮挡 / 事实错 / 该有的画面没有 / 出安全区；中 = 节拍偏差、样式不一致、静止过长、字数超标；低 = 间距对齐微调。
修复按集派子代理（一次只修一到两集，附问题表），改完 build + check；主循环只对改动镜重看截图（复验：已修 / 部分 / 未修 / 新问题）。两轮后目标：高 0 / 中 0 / 低 ≤ 5。

## 3. 交付件（三条命令是机械活，派 fast-worker 跑，主循环只看结果）
```bash
python3 $HDE/lib/cover.py 第N集 <镜号> 交付/封面_第N集.png      # 指定镜抓帧 + 标题 + Logo（若有）
python3 $HDE/lib/chapters.py 第N集 --md 脚本/<集>.md > 交付/章节_第N集.txt   # 由 timeline.json 生成章节时间戳
python3 $HDE/lib/preview_pack.py 第N集 交付/预审包_第N集.html --md 脚本/<集>.md   # 全部插画 + 屏幕文字 + 旁白，逐条可勾（预设要求时才出）
python3 $HDE/lib/progress.py . 第N集 交付 "✅ <日期>"
```
`--md` 现在可以不给：两个脚本会从 `series.json` 往上定位项目、按集号自己找到脚本 md，并在 stderr 说明用了哪个文件。显式传 `--md` 仍以命令行为准（脚本在别处、或一集对多稿时用）。真找不到才退化——`chapters.py` 的章节名退成旁白摘录、`preview_pack.py` 的屏幕文字变 0 条，那时预审包等于残件。
预审包页脚的「旁白总字数」与本集卡片的「旁白字数」同源（都走 `script_md.narration_chars`，去标点空白计数）。2026-09-18 之前 `preview_pack.py` 只去空白不去标点，同一个标签在两处给出两个数，现已统一——老预审包上的数字会比现在偏大，不是 bug。
交付目录里放：最终版完整 mp4（1920×1080 / 30fps / H.264）、`.srt`、封面、章节、README（[templates/delivery-readme.md](../templates/delivery-readme.md)：成片规格、每集标题时长与贯穿隐喻、配音来源、质检结论、已知保留项、发布前必做）。只放最终版；过程件留工程目录；同名不同内容的旧成片保留并加版本后缀。
交付目录的绝对位置与是否要预审包按预设；通用版缺省 `<项目根>/交付/`。

## 4. 品牌与来源（缺省，预设可改）
- Logo 可选：`assets/logo.png` 存在时片头角标 + 片尾大 Logo，由程序层叠加原图，不让生图模型画；透明底原图允许按有效边界裁切显示，不改原文件。
- 对外稿件、旁白、字幕、片尾不主动加原作者、原视频链接、参考资料页或风格借鉴说明；知识本身需要的机构、产品、论文名可以保留。核验链接与材料映射留在 `_grounding/`，不进交付目录。
- 第三方素材的 LICENSE / NOTICE 不删；确有署名要求的素材优先换用可免署名的。

## 5. 复盘回填（每个系列交付后必做，10 分钟）
1. 新坑 → [gotchas.md](gotchas.md)，按「现象 / 根因 / 修法」写；**坑对应的脚本当场改**（写进坑表而不改脚本等于没修）。
2. 新的镜头画法 → [03-shot-patterns.md](03-shot-patterns.md) 加一行，指向源码。
3. 用了预设的项目 → 该预设指定的判例库或规则文件追加本轮用户拍板的判断。
4. 量化基线若有新集数据 → `shot_metrics.py --baseline` 重跑，阈值变了就改 03-production 的表并注明日期。
5. `进度.md` 全部格子收尾；`_chain/plan.md` 修订记录写"交付完成 + 对账结果"。
