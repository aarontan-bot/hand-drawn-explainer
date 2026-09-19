#!/bin/zsh
# 环境预检：逐项打印 OK / WARN / FAIL，任一 FAIL 退出码 1。
# 用法：doctor.sh [--bench <mp4>]

set -u
setopt local_options pipe_fail

FAIL_COUNT=0
WARN_COUNT=0
OK_COUNT=0

report() {
  # report <STATUS> <项目> <说明>
  local lvl=$1 item=$2 note=$3
  printf '%-4s  %-14s  %s\n' "$lvl" "$item" "$note"
  case "$lvl" in
    OK)   ((OK_COUNT++)) ;;
    WARN) ((WARN_COUNT++)) ;;
    FAIL) ((FAIL_COUNT++)) ;;
  esac
}

BENCH_MP4=""
if [[ "${1:-}" == "--bench" ]]; then
  BENCH_MP4="${2:-}"
fi

# 1. ffmpeg + libass
if command -v ffmpeg >/dev/null 2>&1; then
  if ffmpeg -hide_banner -buildconf 2>&1 | grep -q enable-libass; then
    report OK ffmpeg "$(command -v ffmpeg)（带 libass）"
  else
    if [[ -x /opt/homebrew/opt/ffmpeg-full/bin/ffmpeg ]]; then
      report WARN ffmpeg "当前 PATH 里的 ffmpeg 不带 libass，请把 /opt/homebrew/opt/ffmpeg-full/bin 放到 PATH 前面"
    else
      report FAIL ffmpeg "$(command -v ffmpeg) 不带 libass，且找不到 ffmpeg-full 备选"
    fi
  fi
else
  report FAIL ffmpeg "PATH 里找不到 ffmpeg"
fi

# 2. ffprobe
if command -v ffprobe >/dev/null 2>&1; then
  report OK ffprobe "$(command -v ffprobe)"
else
  report FAIL ffprobe "PATH 里找不到 ffprobe"
fi

# 3. node >= 18
if command -v node >/dev/null 2>&1; then
  NODE_MAJOR=$(node --version | sed -E 's/^v([0-9]+).*/\1/')
  if (( NODE_MAJOR >= 18 )); then
    report OK node "$(node --version)"
  else
    report FAIL node "$(node --version)，需要 >= 18"
  fi
else
  report FAIL node "PATH 里找不到 node"
fi

# 4. hyperframes（锁版本 0.8.20）
if command -v npx >/dev/null 2>&1; then
  if HF_VER=$(npx --no-install hyperframes@0.8.20 --version 2>/dev/null); then
    report OK hyperframes "$HF_VER（已缓存）"
  else
    report WARN hyperframes "hyperframes@0.8.20 未缓存，首次渲染会自动下载"
  fi
else
  report FAIL hyperframes "PATH 里找不到 npx"
fi

# 5. python3 依赖
if command -v python3 >/dev/null 2>&1; then
  if PY_INFO=$(python3 -c "import PIL, numpy; print(f'Pillow {PIL.__version__}, numpy {numpy.__version__}')" 2>/dev/null); then
    report OK python3 "$PY_INFO"
  else
    report FAIL python3 "缺 Pillow 或 numpy（pip install Pillow numpy）"
  fi
else
  report FAIL python3 "PATH 里找不到 python3"
fi

# 6. Chrome
CHROME_BIN="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
if [[ -x "$CHROME_BIN" ]]; then
  report OK Chrome "$CHROME_BIN"
else
  report FAIL Chrome "找不到 Chrome（默认路径或 \$CHROME 都没有）"
fi

# 6.5 中文字体（封面烧字用；缺了不报错只静默回退成黑体，封面和片内对不上）
FONT_OUT=$(python3 "$(dirname "$0")/fonts.py" 2>&1)
if print -- "$FONT_OUT" | grep -q '找不到'; then
  report WARN 中文字体 "苹方有字重找不到，封面会回退黑体：$(print -- "$FONT_OUT" | grep '找不到' | head -1)"
else
  report OK 中文字体 "苹方 Regular/Medium/Semibold 都在"
fi

# 7. TTS 密钥（只报存在与否，绝不打印内容）
TTS_KEY_FILE="${VOLCENGINE_TTS_KEY_FILE:-$HOME/.config/nikola-video/volcengine-tts.key}"
if [[ -n "${VOLCENGINE_TTS_API_KEY:-}" ]]; then
  report OK TTS密钥 "环境变量 VOLCENGINE_TTS_API_KEY 已设置"
elif [[ -s "$TTS_KEY_FILE" ]]; then
  report OK TTS密钥 "密钥文件存在且非空：$TTS_KEY_FILE"
else
  report WARN TTS密钥 "未找到（配音阶段才需要）：环境变量或 $TTS_KEY_FILE"
fi

# 8. codex CLI
if command -v codex >/dev/null 2>&1; then
  report OK codex "$(command -v codex)"
else
  report WARN codex "PATH 里找不到 codex（只影响 Codex 生图路径）"
fi

# 9. 磁盘余量（/tmp 与当前目录所在卷都要 >= 20GB）
check_disk() {
  # 注意：zsh 的 $path（小写）是和 $PATH 绑定的特殊数组，局部变量绝不能叫这个名字
  local target=$1 label=$2
  local avail_kb avail_gb
  avail_kb=$(df -k "$target" 2>/dev/null | tail -1 | awk '{print $4}')
  if [[ -z "$avail_kb" ]]; then
    report WARN "磁盘($label)" "df 读不到 $target 的可用空间"
    return
  fi
  avail_gb=$((avail_kb / 1024 / 1024))
  if (( avail_gb >= 20 )); then
    report OK "磁盘($label)" "${avail_gb}GB 可用（$target）"
  else
    report FAIL "磁盘($label)" "仅 ${avail_gb}GB 可用（$target），长片渲染会索要几十 GB 临时空间"
  fi
}
check_disk /tmp "/tmp"
check_disk . "当前目录"

# 可选：--bench <mp4>
if [[ -n "$BENCH_MP4" ]]; then
  if [[ -f "$BENCH_MP4" ]]; then
    DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$BENCH_MP4" 2>/dev/null)
    if [[ -n "$DUR" ]]; then
      report OK bench "$BENCH_MP4 时长 ${DUR}s；本机渲染耗时请参考 reports/render.log"
    else
      report WARN bench "ffprobe 读不到 $BENCH_MP4 的时长"
    fi
  else
    report WARN bench "文件不存在：$BENCH_MP4"
  fi
fi

echo "----"
echo "汇总：OK=$OK_COUNT  WARN=$WARN_COUNT  FAIL=$FAIL_COUNT"

if (( FAIL_COUNT > 0 )); then
  exit 1
fi
exit 0
