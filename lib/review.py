"""每个镜头取一帧（最后一个事件后 1.8 秒）拼成总览图。用法：review.py <集目录> <mp4> <输出前缀>"""
import json, os, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fonts
E = Path(sys.argv[1]); mp4 = sys.argv[2]; pre = sys.argv[3]
d = json.loads((E / 'timeline.json').read_text())
font = fonts.mono(26)   # 原来写死 Helvetica.ttc 路径且零回退，系统挪走字体就直接崩
frames = []
for s in d['scenes']:
    ev = list(s['events'].values())
    t = min(s['end'] - 0.5, (max(ev) + 1.8) if ev else s['start'] + 2.5)
    f = f'/tmp/_rv_{os.getpid()}_{s["no"]:02}.png'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.2f}', '-i', mp4, '-frames:v', '1', '-vf', 'scale=640:360', f])
    im = Image.open(f); ImageDraw.Draw(im).text((560, 320), f'{s["no"]:02}', fill=(0, 0, 220), font=font); frames.append(im)
for k in range(0, len(frames), 9):
    part = frames[k:k + 9]; sheet = Image.new('RGB', (1920, 1080), 'gray')
    for i, im in enumerate(part):
        sheet.paste(im, ((i % 3) * 640, (i // 3) * 360))
    sheet.save(f'{pre}_{k // 9 + 1}.png')
print(len(frames))
