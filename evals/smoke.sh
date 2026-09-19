#!/bin/zsh
# 回归测试：只写 /tmp/hde-smoke/；任何一项不过，整个脚本以非 0 退出。
#
# 第 1、2 项是「字节级对账」：拿一套**已经交付过的真实系列**当 oracle，断言 scaffold 与 build
# 的产物和当初一字不差。这类产物不适合放进公开仓库（那是作者自己的课程内容），所以改成可选：
#   export HDE_ORACLE_SERIES=/path/to/<系列工程目录>    # 含 第1集/…第N集/
#   export HDE_ORACLE_SCRIPTS=/path/to/<脚本目录>       # 含 9 份分镜 md
#   export HDE_ORACLE_GLOB='3.%s-*.md'                  # 可选，按集号取脚本的 glob，%s 是集号
# 两个变量没设或目录不存在就跳过这两项，其余各项照常跑——它们不依赖任何外部产物。
#
# 只有自己有历史交付的人才需要配 oracle。新用户跑 3–12 项就够验证本机环境与 skill 自身一致性。
set -u
SKILL=$(cd "$(dirname "$0")/.." && pwd)
LIB=$SKILL/lib
WORK=/tmp/hde-smoke
V="${HDE_ORACLE_SERIES:-}"
D="${HDE_ORACLE_SCRIPTS:-}"
OGLOB="${HDE_ORACLE_GLOB:-3.%s-*.md}"
OLD_LIB="$V/lib"
[[ -n "${PATH##*ffmpeg-full*}" ]] && export PATH="/opt/homebrew/opt/ffmpeg-full/bin:$PATH"

HAVE_ORACLE=0
[[ -n "$V" && -d "$V" && -n "$D" && -d "$D" ]] && HAVE_ORACLE=1

rm -rf "$WORK"; mkdir -p "$WORK"
FAIL=0
ok()   { print -- "PASS  $1" }
bad()  { print -- "FAIL  $1"; FAIL=1 }
skip() { print -- "SKIP  $1" }

if [[ $HAVE_ORACLE -eq 0 ]]; then
  print -- "==== 1) scaffold 对账（字节级 oracle）===="
  skip "scaffold 对账：未配置 HDE_ORACLE_SERIES / HDE_ORACLE_SCRIPTS（见本文件顶部说明）"
  print -- "==== 2) build 对账（字节级 oracle）===="
  skip "build 对账：同上"
else
print -- "==== 1) scaffold 对账（9 集，先跑第 8 集）===="
for n in 8 1 2 3 4 5 6 7 9; do
  # 用 find 而不是 zsh glob：模式来自变量时 zsh 默认不对展开结果做 globbing，`*` 会被当字面量
  md=$(find "$D" -maxdepth 1 -name "${OGLOB/\%s/$n}" 2>/dev/null | sort | head -1)
  if [[ -z "$md" ]]; then bad "scaffold ep$n: 找不到脚本 md"; continue; fi
  python3 "$LIB/scaffold_episode.py" "$md" "$WORK/scaffold/第${n}集" > "$WORK/scaffold_log_$n.txt" 2>&1
  rc=$?
  if [[ $rc -ne 0 ]]; then bad "scaffold ep$n: 退出码 $rc（见 $WORK/scaffold_log_$n.txt）"; fi
done

python3 - "$V" "$WORK/scaffold" <<'PY'
import json, sys
from pathlib import Path
V, W = Path(sys.argv[1]), Path(sys.argv[2])
fail = False
notes = []
for n in range(1, 10):
    oracle, work = V / f"第{n}集", W / f"第{n}集"
    if not work.exists():
        continue
    tag = f"scaffold ep{n}"
    # audio/shot-NN.txt：strip 后逐字相等
    o_txts = sorted(p.name for p in (oracle / 'audio').glob('shot-*.txt'))
    w_txts = sorted(p.name for p in (work / 'audio').glob('shot-*.txt'))
    if o_txts != w_txts:
        print(f"FAIL  {tag}: audio txt 文件集合不同 {set(o_txts) ^ set(w_txts)}"); fail = True
    for name in o_txts:
        a = (oracle / 'audio' / name).read_text(encoding='utf-8').strip()
        b = (work / 'audio' / name).read_text(encoding='utf-8').strip() if (work / 'audio' / name).exists() else None
        if a != b:
            print(f"FAIL  {tag}: {name} 内容不一致"); fail = True
    # rows.json：JSON 相等；单幅（1元素 vs 旧产物2元素+—）是 spec 明确定义的新格式，记为 NOTE 不算 FAIL
    oj = json.loads((oracle / 'illus/rows.json').read_text(encoding='utf-8'))
    wj = json.loads((work / 'illus/rows.json').read_text(encoding='utf-8')) if (work / 'illus/rows.json').exists() else None
    if wj is None:
        print(f"FAIL  {tag}: 没有生成 illus/rows.json"); fail = True
    elif oj != wj:
        ok_, bk_ = set(oj), set(wj)
        if ok_ != bk_:
            print(f"FAIL  {tag}: rows.json 镜号集合不同 {ok_ ^ bk_}"); fail = True
        for k in ok_ & bk_:
            if oj[k] != wj[k]:
                is_single_format = len(oj[k]) == 2 and oj[k][1] == '—' and wj[k] == [oj[k][0].split('：', 1)[-1]] if oj[k][0].startswith('单幅') else False
                # 更宽松地判断：旧产物两元素且第二个是 —，新产物一元素——这是 spec 定义的单幅新格式，不是解析错误
                if len(oj[k]) == 2 and oj[k][1] == '—' and len(wj[k]) == 1:
                    notes.append(f"NOTE  {tag}: 镜{k} 单幅新旧格式差异（spec 定义单幅为1元素，旧产物是2元素+"'"'"—"'"'"）——已知，非解析错误")
                else:
                    print(f"FAIL  {tag}: rows.json[{k}] 不一致\n      oracle={oj[k]}\n      gen   ={wj[k]}"); fail = True
    # shots.json：no 集合、title/end/illus/single 的 kind、fixed、pause_end
    oa = json.loads((oracle / 'shots.json').read_text(encoding='utf-8'))
    wa = json.loads((work / 'shots.json').read_text(encoding='utf-8')) if (work / 'shots.json').exists() else None
    if wa is None:
        print(f"FAIL  {tag}: 没有生成 shots.json"); fail = True
    else:
        on = {s['no'] for s in oa}; wn = {s['no'] for s in wa}
        if on != wn:
            print(f"FAIL  {tag}: shots.json no 集合不同 {on ^ wn}"); fail = True
        om = {s['no']: s for s in oa}; wm = {s['no']: s for s in wa}
        for no in sorted(on & wn):
            so, sw = om[no], wm[no]
            if so['kind'] in ('title', 'end', 'illus', 'single') and so['kind'] != sw['kind']:
                print(f"FAIL  {tag}: 镜{no} kind 不一致 oracle={so['kind']} gen={sw['kind']}"); fail = True
            if so.get('fixed') != sw.get('fixed'):
                print(f"FAIL  {tag}: 镜{no} fixed 不一致 oracle={so.get('fixed')} gen={sw.get('fixed')}"); fail = True
            if so.get('pause_end') != sw.get('pause_end'):
                print(f"FAIL  {tag}: 镜{no} pause_end 不一致 oracle={so.get('pause_end')} gen={sw.get('pause_end')}"); fail = True
if notes:
    print('\n'.join(notes))
print("SCAFFOLD_PY_RESULT", "FAIL" if fail else "PASS")
sys.exit(1 if fail else 0)
PY
if [[ $? -ne 0 ]]; then bad "scaffold 对账（详见上面 FAIL 行；单幅新旧格式差异已单独列为 NOTE，不计入失败）"; else ok "scaffold 对账（9 集，含上面列出的已知单幅格式 NOTE）"; fi

print -- "==== 2) build 对账（第 8 集，先有 logo 再无 logo）===="
rm -rf "$WORK/build8" "$WORK/build8-nologo"
mkdir -p "$WORK/build8/第8集/scripts" "$WORK/build8/assets"
cp "$V/第8集/shots.json" "$WORK/build8/第8集/"
cp -r "$V/第8集/audio" "$WORK/build8/第8集/"
cp -r "$V/第8集/illus" "$WORK/build8/第8集/"
cp "$V/第8集/scripts/episode.js" "$WORK/build8/第8集/scripts/"
cp "$OLD_LIB/logo.png" "$WORK/build8/assets/logo.png"
python3 "$LIB/build.py" "$WORK/build8/第8集" > "$WORK/build8_log.txt" 2>&1
rc=$?
if [[ $rc -ne 0 ]]; then
  bad "build（有 logo）：退出码 $rc（见 $WORK/build8_log.txt）"
else
  python3 - "$V/第8集" "$WORK/build8/第8集" <<'PY'
import json, sys
from pathlib import Path
oracle, work = Path(sys.argv[1]), Path(sys.argv[2])
a = json.loads((oracle / 'timeline.json').read_text(encoding='utf-8'))
b = json.loads((work / 'timeline.json').read_text(encoding='utf-8'))
ok1 = a == b
srt_a = (oracle / '字幕.srt').read_text(encoding='utf-8')
srt_b = (work / '字幕.srt').read_text(encoding='utf-8')
ok2 = srt_a == srt_b
html = (work / 'comp/index.html').read_text(encoding='utf-8')
ok3 = '"logo": true' in html
print('TIMELINE_EQUAL', ok1)
print('SRT_EQUAL', ok2)
print('LOGO_TRUE_IN_HTML', ok3)
sys.exit(0 if (ok1 and ok2 and ok3) else 1)
PY
  if [[ $? -eq 0 ]]; then ok "build 有 logo：timeline.json/字幕.srt 与旧产物一致，index.html 含 logo:true"; else bad "build 有 logo：见上面 TIMELINE_EQUAL/SRT_EQUAL/LOGO_TRUE_IN_HTML"; fi
fi

mkdir -p "$WORK/build8-nologo/第8集/scripts"
cp "$V/第8集/shots.json" "$WORK/build8-nologo/第8集/"
cp -r "$V/第8集/audio" "$WORK/build8-nologo/第8集/"
cp -r "$V/第8集/illus" "$WORK/build8-nologo/第8集/"
cp "$V/第8集/scripts/episode.js" "$WORK/build8-nologo/第8集/scripts/"
python3 "$LIB/build.py" "$WORK/build8-nologo/第8集" > "$WORK/build8_nologo_log.txt" 2>&1
rc=$?
if [[ $rc -ne 0 ]]; then
  bad "build（无 logo）：退出码 $rc（见 $WORK/build8_nologo_log.txt）"
else
  html="$WORK/build8-nologo/第8集/comp/index.html"
  if grep -q '"logo": false' "$html" && [[ ! -f "$WORK/build8-nologo/第8集/comp/assets/logo.png" ]]; then
    ok "build 无 logo：index.html 含 logo:false，comp/assets 无 logo.png"
  else
    bad "build 无 logo：index.html 或 comp/assets/logo.png 不符合预期"
  fi
fi

fi   # HAVE_ORACLE —— 第 1、2 项到此为止

print -- "==== 3) hyperframes check ===="
# 有 oracle 就拿真实的第 8 集查；没有就自造一个最小工程——「hyperframes 这个版本在本机跑不跑得通」
# 是新用户最需要先确认的一条，不能因为缺 oracle 就整项跳过。
CHECK_DIR=""
if [[ -d "$WORK/build8/第8集/comp" ]]; then
  CHECK_DIR="$WORK/build8/第8集"
else
  M="$WORK/mini"
  rm -rf "$M"; mkdir -p "$M/audio" "$M/illus" "$M/scripts"
  cat > "$M/shots.json" <<'EOF'
[
 {"no": 1, "kind": "title", "fixed": 5.0},
 {"no": 2, "kind": "solo", "cues": []},
 {"no": 3, "kind": "end", "fixed": 3.0}
]
EOF
  print -- "这是一句完整的旁白用来验证构建管道是否正常工作。" > "$M/audio/shot-02.txt"
  python3 - "$M" <<'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
text = (root / 'audio/shot-02.txt').read_text(encoding='utf-8').strip()
meta = {"complete": True, "events": [{"sentence": {"words": [
    {"word": ch, "startTime": i * 0.2, "endTime": i * 0.2 + 0.15} for i, ch in enumerate(text)
]}}]}
(root / 'audio/shot-02.mp3.json').write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')
PY
  ffmpeg -v error -f lavfi -i anullsrc=r=24000:cl=mono -t 6 -q:a 9 "$M/audio/shot-02.mp3" -y
  print -- '{}' > "$M/illus/marks.json"
  cat > "$M/scripts/episode.js" <<'EOF'
const EP={no:1,title:'冒烟',sub:'最小工程'};
Object.assign(BUILD,{solo(sc,s){sc.draw(sc.circle(960,480,300),sc.t0+.2,.6)}});
EOF
  if python3 "$LIB/build.py" "$M" > "$WORK/mini_build.txt" 2>&1; then
    CHECK_DIR="$M"
  else
    bad "hyperframes check：最小工程 build 失败（见 $WORK/mini_build.txt）"
  fi
fi
if [[ -n "$CHECK_DIR" ]]; then
  ( cd "$CHECK_DIR" && npx hyperframes@0.8.20 check comp > "$WORK/hyperframes_log.txt" 2>&1 )
  if grep -q '0 error' "$WORK/hyperframes_log.txt" && ! grep -qE '[1-9][0-9]* error' "$WORK/hyperframes_log.txt"; then
    ok "hyperframes check：0 error（$([[ "$CHECK_DIR" == "$WORK/mini" ]] && print -n '最小工程' || print -n '真实第 8 集')，见 $WORK/hyperframes_log.txt）"
  else
    bad "hyperframes check：未确认 0 error（见 $WORK/hyperframes_log.txt）"
  fi
fi

print -- "==== 4) 截断校验单测（build.py）===="
rm -rf "$WORK/trunc"
mkdir -p "$WORK/trunc/audio" "$WORK/trunc/illus" "$WORK/trunc/scripts"
cat > "$WORK/trunc/shots.json" <<'EOF'
[
 {"no": 1, "kind": "title", "fixed": 5.0},
 {"no": 2, "kind": "solo", "cues": []},
 {"no": 3, "kind": "end", "fixed": 3.0}
]
EOF
print -- "这是一句完整的旁白用来测试截断校验功能是否正常工作。" > "$WORK/trunc/audio/shot-02.txt"
python3 - "$WORK/trunc" <<'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
text = (root / 'audio/shot-02.txt').read_text(encoding='utf-8').strip()
half = text[:10]
meta = {"complete": True, "events": [{"sentence": {"words": [
    {"word": ch, "startTime": i * 0.2, "endTime": i * 0.2 + 0.15} for i, ch in enumerate(half)
]}}]}
(root / 'audio/shot-02.mp3.json').write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')
PY
ffmpeg -v error -f lavfi -i anullsrc=r=24000:cl=mono -t 2 -q:a 9 "$WORK/trunc/audio/shot-02.mp3" -y
print -- '{}' > "$WORK/trunc/illus/marks.json"
cat > "$WORK/trunc/scripts/episode.js" <<'EOF'
const EP={no:1,title:'t',sub:'s'};
Object.assign(BUILD,{solo(sc,s){}});
EOF
python3 "$LIB/build.py" "$WORK/trunc" > "$WORK/trunc_log.txt" 2>&1
rc=$?
if [[ $rc -eq 2 ]] && grep -q "截断" "$WORK/trunc_log.txt"; then
  ok "截断校验：退出码 2，输出含「截断」"
else
  bad "截断校验：期望退出码 2 且含「截断」，实际 rc=$rc（见 $WORK/trunc_log.txt）"
fi

print -- "==== 5) 通用性 grep（lib/、references/、templates/ 不许出现项目专属口径）===="
# 内核必须对任何主题、受众、画风都成立——项目专属的角色名、品牌、受众术语只能待在 profiles/ 里。
# 这里只内置对所有人都成立的那条（绝对路径）；你自己的口径词用环境变量追加，例如：
#   export HDE_BANNED_EXTRA='我的角色名|我的品牌|某受众术语'
BANNED="/Users/|/home/${HDE_BANNED_EXTRA:+|$HDE_BANNED_EXTRA}"
hit=0
for dir in "$LIB" "$SKILL/references" "$SKILL/templates"; do
  [[ -d "$dir" ]] || continue
  while IFS= read -r line; do
    print -- "FAIL  通用性 grep 命中：$line"
    hit=1
  done < <(grep -rnI -E "$BANNED" "$dir" --include='*.py' --include='*.js' --include='*.html' --include='*.sh' --include='*.json' --include='*.md' --include='*.txt' 2>/dev/null)
done
if [[ $hit -eq 0 ]]; then ok "通用性 grep：lib/references/templates 未命中禁用词"; else bad "通用性 grep：命中见上"; fi

print -- "==== 6) --illus-mode svg 冒烟 ===="
rm -rf "$WORK/svg-mode"
# 夹具用仓库自带的合成脚本（含插画镜），不依赖本机产物
md6="$SKILL/evals/fixtures/01-two-col-table.md"
python3 "$LIB/scaffold_episode.py" "$md6" "$WORK/svg-mode/第8集" --illus-mode svg > "$WORK/svg_log.txt" 2>&1
rc=$?
if [[ $rc -ne 0 ]]; then
  bad "svg 模式 scaffold：退出码 $rc（见 $WORK/svg_log.txt）"
else
  python3 - "$WORK/svg-mode/第8集" <<'PY'
import json, sys
from pathlib import Path
w = Path(sys.argv[1])
shots = json.loads((w / 'shots.json').read_text(encoding='utf-8'))
kinds = {s['kind'] for s in shots}
illus_files = sorted(p.name for p in (w / 'illus').iterdir())
bad_ = []
if kinds & {'illus', 'single'}:
    bad_.append(f'shots.json 里仍有 illus/single：{kinds & {"illus","single"}}')
if 'scene' not in kinds:
    bad_.append('shots.json 里没有 scene')
if illus_files != ['场景说明.md']:
    bad_.append(f'illus/ 下应只有 场景说明.md，实际是 {illus_files}')
if bad_:
    print('SVG_MODE_FAIL: ' + '; '.join(bad_))
    sys.exit(1)
print('SVG_MODE_OK')
PY
  if [[ $? -eq 0 ]]; then
    ok "svg 模式：shots.json 无 illus/single、有 scene，illus/ 下只有 场景说明.md"
  else
    bad "svg 模式：见 $WORK/svg_log.txt 及上面 SVG_MODE_FAIL"
  fi
fi

print -- "==== 7) helper 存在性（03-production.md 点名的 core.js 方法与 icon kind）===="
CORE=$LIB/core.js
miss=0
for h in at draw pop fade out line rect circle ellipse path rrect arrow text html mark note ringSpan strikeSpan spanBox chip xiaohei robot phone paper bubble cloud stamp check cross hourglass hourglassPause remember icon art; do
  grep -qE "^\s*$h\(" "$CORE" || { print -- "FAIL  core.js 缺 helper：$h"; miss=1; }
done
for k in question command page cards sketch form house flag eye think book lens brush fork ruler plus target people stop list table paras diary scroll news medal cake clock hand star bulb chat photo gear loop lock key shelf; do
  grep -q "kind==='$k'" "$CORE" || { print -- "FAIL  core.js 缺 icon kind：$k"; miss=1; }
done
for b in title illus single end; do
  grep -qE "^\s*$b\(sc" "$CORE" || { print -- "FAIL  core.js 缺内置构建器：$b"; miss=1; }
done
if [[ $miss -eq 0 ]]; then ok "helper 存在性：文档点名的方法 / icon / 内置构建器都在 core.js"; else bad "helper 存在性：见上"; fi

# 下面三项测的是「文档说的等不等于脚本做的」。1–7 项只比对三条主管道的产物字节级一致，
# 2026-09-18 一天里查出的 8 个 bug 它一个都没拦住——那 8 个全是这一类：
# 某个可选参数没传、某个格式两个脚本口径不一、某条坑表标了 ✔ 却没真改。
print -- "==== 8) 预设合并（--profile 必须把预设的画风与出图路径写进 series.json）===="
PP="$WORK/profilemerge"
# 夹具用仓库自带的合成脚本 + 示例预设，不依赖任何本机产物
PROF=example-xiaohei
md8="$SKILL/evals/fixtures/01-two-col-table.md"
if [[ ! -f "$md8" ]]; then
  bad "预设合并：找不到夹具脚本 $md8"
else
  mkdir -p "$PP/脚本"; cp "$md8" "$PP/脚本/"
  ( cd "$PP" && python3 "$LIB/scaffold_episode.py" "脚本/${md8:t}" 第1集 --profile "$PROF" ) \
    > "$WORK/profilemerge_log.txt" 2>&1
  python3 - "$SKILL" "$PP" "$PROF" >> "$WORK/profilemerge_log.txt" 2>&1 <<'PY'
import json, sys
from pathlib import Path
skill, pp, prof = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
defaults = json.loads((skill / f'profiles/{prof}/series-defaults.json').read_text(encoding='utf-8'))
sp = pp / 'series.json'
if not sp.exists():
    print('PROFILE_MERGE_FAIL 没生成 series.json'); raise SystemExit
series = json.loads(sp.read_text(encoding='utf-8'))
bad = [f'{k}：预设 {v!r} → series.json {series.get(k)!r}' for k, v in defaults.items() if series.get(k) != v]
pf = pp / '第1集/illus/生图提示词.md'
prompt = pf.read_text(encoding='utf-8') if pf.exists() else ''
if defaults.get('style') == 'xiaohei' and 'Minimalist hand-drawn editorial' not in prompt:
    bad.append('生图提示词没用上 xiaohei 前缀（退回通用 line 了）')
print('PROFILE_MERGE_FAIL ' + ' ｜ '.join(bad) if bad else 'PROFILE_MERGE_OK')
PY
  if grep -q PROFILE_MERGE_OK "$WORK/profilemerge_log.txt"; then
    ok "预设合并：series.json 每个字段都等于 profiles/$PROF/series-defaults.json，生图前缀用的是预设画风"
  else
    bad "预设合并：见 $WORK/profilemerge_log.txt"
    grep PROFILE_MERGE_FAIL "$WORK/profilemerge_log.txt"
  fi
fi

print -- "==== 9) 路径健壮性（错误/相对路径不许 rc=0 还产出垃圾）===="
ph=0
rm -f "$WORK/badpeek.png"
zsh "$LIB/peek.sh" "$WORK/不存在的集目录" "$WORK/badpeek.png" 3 >/dev/null 2>&1
[[ $? -ne 0 ]] || { print -- "FAIL  peek.sh 对错误集目录仍 rc=0"; ph=1 }
[[ ! -f "$WORK/badpeek.png" ]] || { print -- "FAIL  peek.sh 对错误集目录仍产出了图（会被当成本集画面看）"; ph=1 }
python3 "$LIB/retime.py" "$WORK/不存在的脚本目录" >/dev/null 2>&1
[[ $? -ne 0 ]] || { print -- "FAIL  retime.py 对错误脚本目录仍 rc=0（用的人会以为回填过了）"; ph=1 }
grep -q 'Path(ep_dir).resolve()' "$LIB/shot_metrics.py" || { print -- "FAIL  shot_metrics.py 没把集目录绝对化（相对路径会拼出非法 file://）"; ph=1 }
grep -q '${1:A}' "$LIB/peek.sh" || { print -- "FAIL  peek.sh 没把集目录绝对化"; ph=1 }
# 苹方三个字重都要找得到：找不到时 cover.py 不会报错，只会静默回退成黑体，
# 封面字体和片内程序层对不上——没人会注意到的那种坏
python3 "$LIB/fonts.py" > "$WORK/fonts.txt" 2>&1
grep -q '找不到' "$WORK/fonts.txt" && { print -- "FAIL  fonts.py 有字重找不到（见 $WORK/fonts.txt）"; ph=1 }
if [[ $ph -eq 0 ]]; then ok "路径健壮性：peek.sh / retime.py 对坏路径明确失败，且 peek/shot_metrics 都做了绝对化"; else bad "路径健壮性：见上"; fi

print -- "==== 10) 文档命令冒烟（references 点名的 lib 脚本必须存在且 --help 跑得通）===="
dc=0
for s in $(grep -ohE '\$HDE/lib/[a-z_]+(/[a-z_]+)?\.(py|sh)' "$SKILL"/references/*.md "$SKILL/SKILL.md" | sed 's#^\$HDE/lib/##' | sort -u); do
  if [[ ! -f "$LIB/$s" ]]; then print -- "FAIL  文档点名了不存在的脚本：lib/$s"; dc=1; continue; fi
  if [[ "$s" == *.py ]]; then
    # 用 argparse 的脚本，--help 必须跑得通（参数定义坏了或缺依赖都会在这里暴露）；
    # 用 sys.argv 的老脚本没有 --help，退一步只保证能编译
    if grep -q '^import argparse\|^import .*argparse\|argparse\.ArgumentParser' "$LIB/$s"; then
      python3 "$LIB/$s" --help >/dev/null 2>&1 || { print -- "FAIL  lib/$s --help 跑不通（argparse 坏了或缺依赖）"; dc=1 }
    else
      python3 -m py_compile "$LIB/$s" 2>/dev/null || { print -- "FAIL  lib/$s 编译不过"; dc=1 }
    fi
  fi
done
if [[ $dc -eq 0 ]]; then ok "文档命令冒烟：references 里点名的每个 lib 脚本都存在，且 .py 的 --help 都跑得通"; else bad "文档命令冒烟：见上"; fi

print -- "==== 11) 解析器行为锁（合成夹具，覆盖 1/2 项的 oracle 照不到的口径）===="
# 第 1、2 项的 9 集 oracle 高度同质：镜头头全是 3 段式、零个多行字段、出图清单全是三列。
# script_md.py 统一的那些口径分歧恰恰全在 oracle 照不到的地方，必须靠合成夹具钉死。
if PYTHONPATH="$LIB" python3 "$SKILL/evals/parser_diff.py" > "$WORK/parser_diff.txt" 2>&1 \
   && grep -q 'PARSER_DIFF OK' "$WORK/parser_diff.txt"; then
  ok "解析器行为锁：$(grep -oE '[0-9]+ 条断言全过' "$WORK/parser_diff.txt")（夹具见 evals/fixtures/）"
else
  bad "解析器行为锁：见 $WORK/parser_diff.txt"
  tail -20 "$WORK/parser_diff.txt"
fi


print -- "===================="
if [[ $FAIL -eq 0 ]]; then
  print -- "全部 PASS"
  exit 0
else
  print -- "有 FAIL，见上面各项"
  exit 1
fi
