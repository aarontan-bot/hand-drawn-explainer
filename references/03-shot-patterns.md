# 镜头设计模式表（按「画面关系」选，不按领域概念选）

先判断这一镜的旁白讲的是哪一种**画面关系**，再取对应画法与主图；表里没有的关系按 03-production §3 的主图 / 颜色 / 动作规则自己设计，做完把新模式加回来。子代理用到哪种模式，**先看样例截图建立标尺，再读一个源码**。「已有实现」列的键 `EP<集> <构建器>` 指向预设自带的样例库：截图 `$HDE/profiles/<预设名>/shot-gallery/EP<集>-<构建器>.jpg`，源码路径与画面描述在同目录 `index.md`。**仓库不带任何样例库**——它是你用自己已交付的作品一集集攒起来的，所以「已有实现」列的键在你攒出第一批之前都是空的：先按本表的画法与主图规则自行设计，做完把截图和源码路径登记进自己的预设，下次就有标尺了。

## 画面关系 → 画法
| 画面关系 | 画法 | 主图与尺寸 | 已有实现（集 / 构建器） |
|---|---|---|---|
| **本集总览 / 路线图** | 一条路 + 几站、一排格子、一个隐喻物分成几块；每块一个图标 + 2–4 字；旁白一句带过 | 整张总览图 | EP1 overview（五站）、EP2 skeleton（雨伞五骨）、EP3 asks（2×2 四宫格）、EP4 tools（三圆图标）、EP5 map（四级台阶）、EP6 overview（两把锁）、EP7 plan、EP8 panel（六旋钮面板）、EP9 overview（五格工具架） |
| **隐喻物本体**（贯穿全集，讲解 / 答题 / 总结镜复用） | 一件日常物件承担结构：伞骨、画框格、台阶、锁与钥匙、圆环、旋钮、工具架 | 隐喻物占安全区 ≥ 1/3 | EP2 skeleton / checkall / recap（伞）、EP5 steps / recap（台阶）、EP6 fit / pairs（锁钥匙）、EP7 loop / cycle（环）、EP8 dials（旋钮）、EP9 five（工具架） |
| **一个主体 + 若干要素**（逐个亮起） | 左侧编号图标 + 标题问句，右侧要素按节拍弹出（同底色 + 编号，不用颜色分） | 左侧主体图标 ≥ 200 | EP2 task / material / audience / format / limit（共用 rib 子例程）、EP3 role / bound、EP9 extract / judge / expand |
| **缺一格就出问题** | 隐喻物的某一块变灰或打问号 → 红色标缺口 → 补上打勾 | 隐喻物 | EP3 blanks / answer、EP2 quiz / answer、EP2 checkall |
| **有序过程 / 步骤** | 台阶逐级亮起（每级一句），或 输入 → 处理 → 输出 三段 + 箭头自根部长出 | 台阶或处理盒 | EP5 steps / first / flow / cot / list / still（stairs）、EP2 steps（拆三步） |
| **两种做法对比（模糊版 vs 改好版 / 同时改 vs 一次改一处）** | 左右两栏同一物件两种状态，左红叉右绿勾，改好版关键词荧光高亮 | 两栏各一主体 | EP1 compare / clear、EP2 precise / quantify、EP8 once / vague / ans、EP9 modes、EP3 fluff、EP4 cond |
| **分叉判定 / 二选一** | 顶部结果 → 分叉两条线 → 两个色框；或竖虚线分两栏各配图标 | 分叉图 | EP1 fork / fork2 / guess / guess2 |
| **原文卡片 + 标注** | `sc.note` 纸条逐行出现；`mark` 高亮关键词、`ringSpan` 圈问题、`strikeSpan` 划掉；旁边放大镜 / 标签说问题 | 纸条宽 ≥ 900 | EP2 draft、EP4 mix / delim / consist / wr、EP6 worry / method / gaps、EP8 cut / four、EP3 full、EP7 r1 / r2 / r3（结果文件 + 放大镜 + 回环箭头） |
| **原文修改前后** | 同一张纸条：划掉 → 补写（荧光高亮）→ 绿勾"没变弱" | 纸条 | EP2 rewrite、EP6 rewrite、EP8 keep |
| **循环 / 迭代** | 大圆环 + 节点，一段弧高亮表示当前步；折线表示"起点低但持续上升" | 环 ≥ 500 直径 | EP7 loop / cycle / grow、EP7 r1–r3 的回环箭头 |
| **一次只改一处 / 调节** | 旋钮或面板，一次只转一个；结果框跟着变 | 旋钮组 | EP8 panel / once / dials、EP9 knob |
| **记录表 / 三列对照** | 三列表格逐行出现，最后一行圈出结论；或三行问答各配勾 | 表格宽 ≥ 1200 | EP8 log / review、EP7 sum |
| **预测 → 对照** | 预测卡（已填）与结果卡（问号）并排，双向箭头 | 两张卡 | EP7 pred / pred2 |
| **从结果反推缺口** | 左"结果"文件圈问题，右"提示词"文件空位加号，箭头连 | 两份文件 | EP7 rev |
| **多个类别并列**（四种场景、六种形式、三件事） | 一排圆圈图标 + 2–4 字标签；≥5 项先分组 | 图标行 | EP1 forms、EP3 cases、EP4 demo3、EP2 tips、EP9 quiz 底部工具行 |
| **三档递增 / 取舍** | 三个方框内容量递增，中间或目标档绿框 | 三框 | EP4 zof |
| **量级可感化** | 长度用线长、数量用格子、上限用一叠纸顶部红线 | 对照物 | EP2 quantify、EP9 thick（聊天记录本上限） |
| **检查 / 自检**（担心点 ↔ 核对办法） | 锁与钥匙：钥匙插入锁孔打勾；对不上打叉 | 锁钥匙 | EP6 overview / worry / method / fit / pairs / answer / swap |
| **进阶按钮 / 可选项** | 圆圈按钮，已学的实心蓝、未学的空心灰并标"下一集" | 按钮行 | EP2 buttons、EP3 adv |
| **地基 vs 加分** | 下方大实心框（地基）+ 上方小框（加分） | 大框 | EP3 order |
| **身份 / 设定卡** | 身份卡（头像 + 两行）+ 示例句 + 后续多轮淡框 | 身份卡 | EP9 ident |
| **互动题 → 揭晓** | 题面画成图（卡片 / 隐喻物带问号）+ `hourglassPause`；揭晓镜复用同图盖章 / 打勾 | 题面主图 | EP1 quiz / answers（盖章）、EP2–EP9 各集 quiz / ans、EP9 turtle |
| **口诀 / 金句** | 两行大字，个别词划掉或高亮，角色小图指向 | 大字 ≥ 72 | EP8 saying、EP4 trust |
| **收尾回扣** | 前文元素淡化为背景 → `sc.remember` 荧光大字 → 贯穿句；系列末集用三行小图标回收前几集隐喻 | 一句话 | 各集 recap、EP9 three |
| **逐步生成 / 一步接一步产出** | 一串等宽格子横排，按节拍逐格填色（蓝 = 已产出的那一步）；停在某一格时上方浮几根长短不同的备选条，最长的落进格子；最后整串收成一条长条表示"接成了一整段" | 格子边长 ≥ 250 | 同一串格子缩到 140 可在答题镜、总结镜复用 |
| **场景与姿态**（illus_mode: svg） | 人物 + 道具 + 环境按对象清单逐件画；表情两点一弧、手势用道具与位置表意 | 人物 ≥ 260 高 | 常用姿态（举卡片、岔路口、趴桌写字、递东西、录像、听声音）建议在自己的预设里开一节「代码画场景样例」记下坐标，积累后复用 |
| **两种失败分岔（一因两果）** | 一条主路走到岔口，两条岔各代表一种失败方式；岔色锁定语义，后面每个补救动作用所属岔的色角标回指这张图 | 整张路线图（约安全区高的 40%） | 让AI把作品做成 · 第1集 `parcel` / `broken` / `sortit`（寄快递：绿岔＝做错了方向，紫岔＝做坏了东西） |
| **清单砍半（主动取舍）** | 候选项竖排同形条目，被砍的画**灰**删除线、整条变灰淡出并左移，剩下的上移；补充项落右侧当注脚、字号小一号，不与主条目同形 | 条目列（不上表格） | 让AI把作品做成 · 第1集 `list7` / `cut4` / `add3`（红只标问题，砍掉用灰 —— 判例 eng-042） |
| **循环 + 一次性地基** | 四块首尾相接成环、短箭头逐段接力（整圈弧绕不开宽条目，也容易撑出安全区）；一次性的那件事画在环**外**，带角标 ＋ 持续转动的齿轮，区别"只做一次"和"只生效一次" | 环（约安全区高的 70%） | 让AI把作品做成 · 第1集 `ring` |
| **"它查不到什么"（能力边界）** | 一张网兜住一部分、网眼漏下一部分；漏下去的图元**留在画面上**，下一镜真的飞进主场景变成主角撞上的那个东西 | 网 ＋ 漏下物 | 让AI把作品做成 · 第1集 `net` → `sAct4` → `sErr2` |

## 贯穿视觉隐喻（每集一个，讲解 / 答题 / 总结镜复用）
已用过的：路线图与两种缺口、雨伞五骨、画框四格、三件工具、摊开的台阶 vs 关着的盒子、锁与钥匙、诊断环、调音台旋钮、五格工具架、一串接龙格子。新系列另起，不用同一隐喻讲不同的事。

## core.js 公共 helper 清单
- **常量**：`INK #1E1C1A`、`RED #D9483B`、`ORG #E8963A`、`BLUE #2F6FDB`、`GREEN #3E9B5F`、`PURPLE #7B5BC7`、`GRAY #6F695F`、`PAPER #FFFFFF`；画布 1920×1080；rough 种子自增（同形状每次抖动不同，全片确定）。
- **时间与入场**：`at draw pop fade out`。
- **基础图形**：`line rect circle ellipse path rrect arrow text html mark`。
- **纸条与标记**：`note`（自动估高，可带标签角标）、`mark`、`ringSpan`、`strikeSpan`、`spanBox`。
- **胶囊**：`chip(x,y,w,label,t,{color,fill,size,h})`（从 7 集重复自建升进来）。
- **角色与道具**：`xiaohei phone robot paper bubble cloud stamp check cross hourglass cloudNode`。
- **图标** `icon(kind,x,y,s)`，kind：`question command page cards sketch form house flag eye think book lens brush fork ruler plus target people stop list table paras diary scroll news medal cake clock hand star bulb chat photo gear loop lock key shelf`。
- **停顿与收尾**：`hourglassPause`、`remember`。
- **插画**：`art(no,single)`；内置构建器 `title illus single end`。

## 升进共享库的候选（同概念不同名，下次开工前合并）
- 台阶：EP5 `stairs`（完整列表组件）vs EP7 `stairsNode`（小图标）。
- 雨伞：EP2 `umbrella` vs EP9 `miniUmbrella`（回顾用缩小版）。
- 单集独有但可复用：EP6 `padlock / padkey`、EP8 `knob / board`、EP9 `taskIcon / shelf`。
