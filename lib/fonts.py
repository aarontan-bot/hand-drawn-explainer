"""字体查找的唯一入口：程序层烧字（封面、抓帧标注）都从这里取，不要各自写死路径。

为什么不能写死 `/System/Library/Fonts/PingFang.ttc`：
macOS 26 起苹方搬进了按需资源目录 `/System/Library/AssetsV2/com_apple_MobileAsset_Font*/
<哈希>.asset/AssetData/PingFang.ttc`，**路径里的哈希每次系统更新都可能变**，只能 glob 不能写死。
写死的后果不是报错而是静默回退到 STHeiti，封面标题字体和片内（苹方）对不上，没人会注意到。

为什么按字体名找 index 而不是写死序号：
PingFang.ttc 是字体集合，一个文件里装着 HK/MO/TC/SC × Regular/Medium/Semibold。本机实测
SC 的三个字重在 index 3/7/11，但这个顺序是 ttc 的打包顺序，不保证跨系统版本稳定，
所以逐个 index 读 `getname()` 比对，命中 ('PingFang SC', <字重>) 才用。

字重对齐 core.js：标题 font-weight 600 → Semibold，正文 500 → Medium，其余 → Regular。
"""
import glob
import sys
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

# 苹方可能在的位置，按优先级；带 * 的走 glob（AssetsV2 路径含哈希）
CJK_PATHS = [
    '/System/Library/Fonts/PingFang.ttc',
    '/Library/Fonts/PingFang.ttc',
    '/System/Library/AssetsV2/com_apple_MobileAsset_Font*/*/AssetData/PingFang.ttc',
]
# 苹方整个找不到时的中文回退，按优先级
CJK_FALLBACKS = [
    '/System/Library/Fonts/STHeiti Medium.ttc',
    '/System/Library/Fonts/STHeiti Light.ttc',
    '/System/Library/Fonts/Songti.ttc',
]
# 只烧数字/英文标注用（等宽优先，读起来齐）
MONO_PATHS = [
    '/System/Library/Fonts/Menlo.ttc',
    '/System/Library/Fonts/SFNSMono.ttf',
    '/System/Library/Fonts/Supplemental/Courier New.ttf',
    '/System/Library/Fonts/Helvetica.ttc',
]

_warned = set()


def _warn_once(msg):
    if msg not in _warned:
        _warned.add(msg)
        print(msg, file=sys.stderr)


def _expand(paths):
    out = []
    for p in paths:
        if '*' in p:
            out.extend(sorted(glob.glob(p)))
        elif Path(p).exists():
            out.append(p)
    return out


@lru_cache(maxsize=None)
def _find_cjk(weight):
    """返回 (字体文件, index)；找不到指定字重就退 Regular，再找不到返回 None。"""
    for path in _expand(CJK_PATHS):
        found_regular = None
        for i in range(32):
            try:
                fam, sty = ImageFont.truetype(path, 10, index=i).getname()
            except Exception:
                break
            if fam != 'PingFang SC':
                continue
            if sty == weight:
                return path, i
            if sty == 'Regular':
                found_regular = (path, i)
        if found_regular:
            _warn_once(f'提示：{Path(path).name} 里没有 PingFang SC {weight}，用 Regular 代替')
            return found_regular
    return None


def cjk(size, weight='Regular'):
    """中文字体（苹方优先）。weight: Regular / Medium / Semibold。"""
    hit = _find_cjk(weight)
    if hit:
        return ImageFont.truetype(hit[0], size, index=hit[1])
    for p in _expand(CJK_FALLBACKS):
        _warn_once(f'警告：本机找不到苹方，回退 {Path(p).name}——封面字体会和片内程序层不一致')
        return ImageFont.truetype(p, size)
    _warn_once('警告：找不到任何中文字体，中文可能显示为方块')
    return ImageFont.load_default()


def mono(size):
    """数字/英文标注用的等宽字体。"""
    for p in _expand(MONO_PATHS):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


if __name__ == '__main__':
    for w in ('Regular', 'Medium', 'Semibold'):
        hit = _find_cjk(w)
        print(f'PingFang SC {w:9} → {hit[0]} #{hit[1]}' if hit else f'PingFang SC {w:9} → 找不到')
    m = _expand(MONO_PATHS)
    print(f'mono          → {m[0] if m else "找不到"}')
