#!/usr/bin/env zsh
# 用法：zsh probe.sh [输出png]
# 新系列第一次派单前，或 core.js 有改动时，先跑一次：把 probe/ 复制到 /tmp，用 skill 内的
# lib/build.py 构建成一份真工程，对每个探针镜在 start+6 秒截图，拼成一张总览图，人看一眼
# 确认 core.js 的图标/角色道具/纸条标注/金句样式在本机渲染正常，再派子代理。
# 不 source peek.sh（避免依赖另一位工作者正在改的文件），但截图与拼图手法照抄它。
set -e
HERE=${0:A:h}                                          # 本脚本所在目录：$HDE/lib/probe
HDE=$(cd "$HERE/../.." && pwd)                          # skill 根，全部相对它推导，不写死任何本机绝对路径
BUILD_PY="$HDE/lib/build.py"                            # 正式路径：skill 内 lib/build.py（另一位工作者会改这份，改完自动用上）
# 兜底 build.py 只认环境变量，不写死任何本机路径：build.py 还没就绪时，调用方可以
# HDE_PROBE_FALLBACK_BUILD_PY=/path/to/旧版/build.py zsh probe.sh 临时验证。
FALLBACK_BUILD_PY=${HDE_PROBE_FALLBACK_BUILD_PY:-}
OUT=${1:-/tmp/hde-probe-overview.png}
CHROME=${CHROME:-"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}

T=/tmp/hde-probe-$$
rm -rf "$T"; cp -R "$HERE" "$T"; rm -f "$T/probe.sh"

if [ -s "$BUILD_PY" ]; then
  RUN_BUILD_PY="$BUILD_PY"
elif [ -n "$FALLBACK_BUILD_PY" ] && [ -s "$FALLBACK_BUILD_PY" ]; then
  echo "警告：$BUILD_PY 还没就绪，临时用 HDE_PROBE_FALLBACK_BUILD_PY=$FALLBACK_BUILD_PY 验证（正式跑请确保 lib/build.py 就位）" >&2
  RUN_BUILD_PY="$FALLBACK_BUILD_PY"
else
  echo "错误：$BUILD_PY 不存在或为空，且没设 HDE_PROBE_FALLBACK_BUILD_PY 兜底" >&2
  exit 1
fi
python3 "$RUN_BUILD_PY" "$T"

# 每个探针镜在 start+6 秒截图（时刻从刚生成的 timeline.json 读）
TIMES_FILE=/tmp/hde-probe-$$-times.txt
python3 - "$T" > "$TIMES_FILE" <<'PY'
import json, sys
d = json.load(open(sys.argv[1] + '/timeline.json'))
print(' '.join(str(round(s['start'] + 6, 2)) for s in d['scenes']))
PY
TIMES=($(cat "$TIMES_FILE")); rm -f "$TIMES_FILE"

C="$T/comp"; i=0; files=()
for t in $TIMES; do
  i=$((i+1))
  sed "s#</script></body></html>#;window.__timelines.main.seek($t);</script></body></html>#" "$C/index.html" > "$C/_probe_$$.html"
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --window-size=1920,1080 --virtual-time-budget=3000 \
    --screenshot=/tmp/hde-probe-$$-$i.png "file://$C/_probe_$$.html" >/dev/null 2>&1
  files+=(/tmp/hde-probe-$$-$i.png)
done
rm -f "$C/_probe_$$.html"

python3 - "$OUT" "${files[@]}" <<'PY'
import sys
from PIL import Image
out = sys.argv[1]; fs = sys.argv[2:]
W, H = 960, 540
cols = 3 if len(fs) > 2 else len(fs)
rows = (len(fs) + cols - 1) // cols
s = Image.new('RGB', (W * cols, H * rows), 'gray')
for i, f in enumerate(fs):
    s.paste(Image.open(f).convert('RGB').resize((W, H)), ((i % cols) * W, (i // cols) * H))
s.save(out)
PY
rm -f /tmp/hde-probe-$$-*.png

echo "探针总览图：$OUT"
echo "构建用的 build.py：$RUN_BUILD_PY"
echo "工程目录（未清理，可自查）：$T"
