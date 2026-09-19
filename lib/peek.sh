#!/bin/zsh
# 用法：peek.sh <集目录绝对路径> <输出png> <秒> [秒...]
# 跳到指定的若干个时刻分别截图，再拼成一张网格图，方便一次看多屏。
# Chrome 路径可用环境变量 CHROME 覆盖（例如换了浏览器安装位置）。
# 集目录必须绝对化：相对路径会拼出非法 file:// URL，Chrome 截出一张 ERR_INVALID_URL 错误页
# 却仍然 rc=0，看图的人以为那就是本集画面（坑表里这条原先标了 ✔ 其实没实现）
E=${1:A}; OUT=$2; shift 2; C=$E/comp; i=0; files=(); T=/tmp/_peek_$$_$RANDOM
[[ -f $C/index.html ]] || { print -u2 "peek.sh: 找不到 $C/index.html —— 第一个参数要是集目录（含 comp/）"; exit 2 }
CHROME=${CHROME:-"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}
for t in "$@"; do i=$((i+1)); sed "s#</script></body></html>#;window.__timelines.main.seek($t);</script></body></html>#" $C/index.html > $C/_peek_$$.html
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --window-size=1920,1080 --virtual-time-budget=3000 --screenshot=${T}_$i.png "file://$C/_peek_$$.html" >/dev/null 2>&1; files+=(${T}_$i.png); done
rm -f $C/_peek_$$.html
# 用系统 python3 拼图（本机已装 Pillow，不再依赖任何 .venv）
python3 - "$OUT" $files <<'PY'
import sys
from PIL import Image
out=sys.argv[1]; fs=sys.argv[2:]; W,H=960,540; cols=2 if len(fs)>1 else 1; rows=(len(fs)+cols-1)//cols
s=Image.new('RGB',(W*cols,H*rows),'gray')
for i,f in enumerate(fs): s.paste(Image.open(f).convert('RGB').resize((W,H)),((i%cols)*W,(i//cols)*H))
s.save(out)
PY
