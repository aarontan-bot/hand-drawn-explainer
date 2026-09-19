#!/bin/zsh
# 按需拉取 handraw-style 的风格参考图（约 23 MB，334 张 webp）。
#
# 本仓库只带风格**定义**（styles.json、画廊页面、文档，约 1 MB），不带图片——把 23 MB 二进制
# 压进 git 历史，对不用 handraw 画风的人是纯负担。要用编号风格（挑编号、给生图模型附参考图）
# 时跑一次这个脚本即可；跑完 images/ 就位，画廊页面也能正常看图。
#
# 用法：zsh fetch-images.sh [commit-ish]
#   不给参数就取 VENDOR-NOTE.md 记录的快照（与本仓库的 styles.json 编号对齐）。
#   给了参数就取那个 commit / 分支 —— 注意上游更新后编号可能与本仓库的 styles.json 不一致。
set -u
DIR=$(cd "$(dirname "$0")" && pwd)
UPSTREAM=https://github.com/yang0/handraw-style.git
# VENDOR-NOTE.md 记录的快照。必须写完整 40 位 SHA —— 按短 SHA fetch 服务端认不出来，
# 会静默退到默认分支的最新版，而上游更新后图片编号可能和本仓库的 styles.json 对不上。
PINNED=6daf50f59693b58e3127598d7db88031498880de
REF=${1:-$PINNED}
TMP=$(mktemp -d /tmp/handraw-fetch.XXXXXX)

cleanup() { rm -rf "$TMP" }
trap cleanup EXIT INT TERM

if [[ -d "$DIR/images" ]]; then
  print -- "images/ 已存在（$(du -sh "$DIR/images" | cut -f1)）。要重新拉取请先删除它。"
  exit 0
fi

print -- "从 $UPSTREAM 取 $REF 的 images/ …"
git init -q "$TMP" || { print -u2 "错误：git init 失败"; exit 1 }
git -C "$TMP" remote add origin "$UPSTREAM"

# 先试只取指定 commit 的浅 fetch（GitHub 支持按 SHA fetch）；失败就退回浅克隆默认分支
if git -C "$TMP" fetch -q --depth 1 origin "$REF" 2>/dev/null; then
  git -C "$TMP" checkout -q FETCH_HEAD -- images 2>/dev/null || {
    print -u2 "错误：$REF 里没有 images/ 目录"; exit 1
  }
else
  print -- "按 $REF 取失败，回退到上游默认分支的最新快照——"
  print -- "  注意：上游若已更新，图片编号可能与本仓库 styles.json 的 268 风格表对不上。"
  git -C "$TMP" fetch -q --depth 1 origin HEAD || { print -u2 "错误：fetch 失败，检查网络或上游地址"; exit 1 }
  git -C "$TMP" checkout -q FETCH_HEAD -- images || { print -u2 "错误：上游没有 images/ 目录"; exit 1 }
fi

mv "$TMP/images" "$DIR/images" || { print -u2 "错误：移动 images/ 失败"; exit 1 }
print -- "完成：$DIR/images（$(du -sh "$DIR/images" | cut -f1)，$(find "$DIR/images" -name '*.webp' | wc -l | tr -d ' ') 张）"

# 编号校验：不管拉到哪个版本，都确认图片编号覆盖得住本仓库 styles.json 里的风格表——
# 上游更新过而 styles.json 没同步的话，挑了编号却找不到参考图，到生图那一步才会发现
python3 - "$DIR" <<'PY'
import json, sys
from pathlib import Path
d = Path(sys.argv[1])
sj = d / 'handdraw-style-prompter/references/styles.json'
img = d / 'images/individual'
if not sj.exists() or not img.exists():
    print('跳过编号校验：找不到 styles.json 或 images/individual'); raise SystemExit
want = {s['number'] for s in json.loads(sj.read_text(encoding='utf-8')) if 'number' in s}
have = {p.stem for p in img.rglob('*.webp')}
missing = sorted(want - have)
if missing:
    print(f'警告：{len(missing)}/{len(want)} 个风格编号没有对应参考图，'
          f'上游版本与本仓库的风格表不一致：{", ".join(missing[:8])}'
          + ('…' if len(missing) > 8 else ''))
    print('     只借画风时可以不附参考图；要附图就重新同步 styles.json 或换一个 commit 重拉。')
else:
    print(f'编号校验通过：{len(want)} 个风格编号都有对应参考图。')
PY
print -- "画廊：$DIR/handdraw-style-prompter/gallery/index.html"
