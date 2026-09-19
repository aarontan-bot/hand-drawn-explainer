#!/bin/zsh
# 用法：move_dl.sh <系列目录> <前缀>
# 把 ~/Downloads/<前缀>_<集两位数>_<镜两位数>.png 归位到 <系列目录>/第N集/illus/<镜号>.png
if [ -z "$1" ] || [ -z "$2" ]; then
  echo "用法：move_dl.sh <系列目录> <前缀>"
  exit 1
fi
B=$1; PREFIX=$2
for f in ~/Downloads/${PREFIX}_*.png(N); do
  n=$(basename $f .png)
  rest=${n#${PREFIX}_}
  ep=${rest%%_*}; no=${rest#*_}
  ep=$((10#$ep))
  dst=$B/第${ep}集/illus/$no.png
  [ -e $dst ] || { mv $f $dst; echo "moved $n -> 第${ep}集/$no" }
done
