"""快速查看一份脚本 md 的每镜「程序/插画」+ 旁白 + 屏幕文字。

用法：python3 shots_dump.py <脚本md路径>
"""
import sys
from pathlib import Path

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB))
import script_md

for s in script_md.parse(Path(sys.argv[1])).shots:
    pause = s.field('停顿')
    pa = f' [停{pause}]' if pause else ''
    scr = ' / '.join(s.screen_items())
    no = s.no_raw.replace('镜 ', '')
    print(f'{no}[{s.method}]{pa} {s.narration}' + (f'\n   屏:{scr}' if scr else ''))
