"""任意一集：按真实词时间戳生成时间轴、字幕与 HyperFrames 工程。

用法：python3 lib/build.py <集目录>（集目录含 shots.json、audio/、illus/、scripts/episode.js）
输出：comp/index.html、comp/assets/、timeline.json、字幕.srt
镜头事件 = 旁白中的触发短语，按出现顺序依次查找；pause_before 在该短语前插入静音。
Logo 可选：优先找 <集目录>/../assets/logo.png（系列级），其次 <集目录>/assets/logo.png；
两处都没有就不放 Logo，index.html 里的数据会带 "logo": false（timeline.json 不含此键，保持与旧版一致）。
"""
import datetime, json, math, re, shutil, subprocess, sys, wave
from pathlib import Path

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB))
import progress
R = Path(sys.argv[1]).resolve()
SR = 24000
N = lambda s: re.sub(r'\W+', '', s).lower()

SHOTS = [(d['no'], d['kind'], [tuple(c) for c in d.get('cues', [])], {k: (tuple(v) if k == 'pause_before' else v) for k, v in d.items() if k in ('fixed', 'pause_end', 'pause_before')}) for d in json.loads((R / 'shots.json').read_text())]
PROGRAM_GAP, ILLUS_GAP = 0.5, 0.9


def pcm_of(path):
    return subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 's16le', '-ar', str(SR), '-ac', '1', '-'])


def silence(sec):
    return b'\0' * (int(sec * SR) * 2)


def split_captions(text):
    groups, cur = [], ''
    for piece in re.findall(r'[^，。！？；：\n]+[，。！？；：]?', text):
        if len(cur) + len(piece) > 22 and cur:
            groups.append(cur); cur = ''
        cur += piece
        if piece.endswith(('。', '？', '！')):
            groups.append(cur); cur = ''
    if cur:
        groups.append(cur)
    merged = []
    for g in groups:
        lead = re.match(r'^\W*', g).group(0)
        if merged and lead:
            merged[-1] += lead
            g = g[len(lead):]
        if g:
            merged.append(g)
    out, q = [], 0
    for g in merged:
        s = ''
        for ch in g:
            if ch == '"':
                s += '“' if q % 2 == 0 else '”'; q += 1
            else:
                s += ch
        out.append(s.replace('……', '').strip())
    fixed = []
    for g in out:
        if fixed and fixed[-1].endswith('“'):
            fixed[-1] = fixed[-1][:-1]; g = '“' + g
        fixed.append(g)
    return [g for g in fixed if N(g)]


def check_truncation(no, words, text):
    """配音的词时间戳拼回的文字必须和旁白原文一致（去标点、忽略大小写比对）；
    不一致最常见的原因是配音被截断，报清楚的错而不是甩一个 assert。"""
    joined = ''.join(w['word'] for w in words)
    nj, nt = N(joined), N(text)
    if nj == nt:
        return
    k = 0
    while k < len(nj) and k < len(nt) and nj[k] == nt[k]:
        k += 1
    done = nj[max(0, len(nj) - 20):]
    remain = nt[k:k + 20]
    print(f'错误：第 {no} 镜配音文字与旁白原文不一致（按去标点、忽略大小写比对）。', file=sys.stderr)
    print(f'  合成到「…{done}」为止', file=sys.stderr)
    print(f'  原文剩余「{remain}…」', file=sys.stderr)
    print('  配音被截断：改措辞后删除该镜 mp3 与 mp3.json 重合成', file=sys.stderr)
    sys.exit(2)


def find_logo():
    """Logo 可选：优先系列级 <集目录>/../assets/logo.png，其次集内 <集目录>/assets/logo.png。"""
    for cand in (R.parent / 'assets/logo.png', R / 'assets/logo.png'):
        if cand.exists():
            return cand
    return None


def main():
    pcm, t = bytearray(), 0.0
    scenes, caps = [], []
    for no, kind, cues, opt in SHOTS:
        s = dict(no=no, kind=kind, start=round(t, 3), events={})
        if 'fixed' in opt:
            pcm.extend(silence(opt['fixed'])); t += opt['fixed']
            s['end'] = round(t, 3); scenes.append(s); continue
        p = R / f'audio/shot-{no:02}.mp3'
        meta = json.loads(p.with_suffix('.mp3.json').read_text())
        assert meta['complete']
        text = (R / f'audio/shot-{no:02}.txt').read_text().strip()
        words = [w for e in meta['events'] if e.get('sentence') for w in e['sentence']['words']]
        check_truncation(no, words, text)
        chars = [dict(st=w['startTime'], en=w['endTime']) for w in words for ch in N(w['word'])]
        src = N(text)
        raw = pcm_of(p)
        # 定位触发短语（按顺序）
        found, cursor = {}, 0
        for key, phrase in cues:
            pos = src.find(N(phrase), cursor)
            assert pos >= 0, (no, phrase)
            found[key] = pos; cursor = pos + 1
        # 句中停顿
        shift_at, shift = None, 0.0
        if 'pause_before' in opt:
            key, sec = opt['pause_before']
            pos = found[key]
            cut = max(chars[pos - 1]['en'], chars[pos]['st'] - 0.08)
            b = int(cut * SR) * 2
            raw = raw[:b] + silence(sec) + raw[b:]
            shift_at, shift = pos, sec
            s['pause'] = [round(t + cut, 3), sec]
        for i, c in enumerate(chars):
            d = shift if shift_at is not None and i >= shift_at else 0.0
            c['st'] += t + d; c['en'] += t + d
        for key, pos in found.items():
            s['events'][key] = round(max(t, chars[pos]['st'] - 0.15), 3)
        pcm.extend(raw)
        dur = len(raw) / 2 / SR
        gap = ILLUS_GAP if kind in ('illus', 'single') else PROGRAM_GAP
        if 'pause_end' in opt:
            s['pause'] = [round(t + dur, 3), opt['pause_end']]
            gap += opt['pause_end']
        pcm.extend(silence(gap))
        pos = 0
        for g in split_captions(text):
            n = len(N(g))
            caps.append(dict(text=g.rstrip('，；：'), start=round(chars[pos]['st'], 3), end=round(chars[pos + n - 1]['en'] + 0.12, 3)))
            pos += n
        assert pos == len(chars), no
        t += dur + gap
        s['end'] = round(t, 3)
        scenes.append(s)
    for a, b in zip(caps, caps[1:]):
        a['end'] = min(a['end'], b['start'])
    duration = math.ceil(t * 30) / 30
    pcm.extend(b'\0' * max(0, int(duration * SR) * 2 - len(pcm)))
    mp = R / 'illus/marks.json'
    marks = json.loads(mp.read_text()) if mp.exists() else {}
    data = dict(duration=duration, scenes=scenes, captions=caps, marks=marks)
    (R / 'timeline.json').write_text(json.dumps(data, ensure_ascii=False, indent=1))

    def ts(x):
        ms = round(x * 1000)
        return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
    (R / '字幕.srt').write_text('\n\n'.join(f"{i+1}\n{ts(c['start'])} --> {ts(c['end'])}\n{c['text']}" for i, c in enumerate(caps)) + '\n')

    out = R / 'comp'
    (out / 'assets').mkdir(parents=True, exist_ok=True)
    for f in ['gsap.min.js', 'rough.js']:
        shutil.copy2(LIB / f, out / 'assets' / f)
    logo = find_logo()
    if logo:
        shutil.copy2(logo, out / 'assets/logo.png')
    for img in sorted((R / 'illus').glob('*.png')):
        if img.name.startswith('ref'):
            continue
        shutil.copy2(img, out / 'assets' / f'illus-{img.stem}.png')
    with wave.open(str(out / 'assets/narration.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm)
    html = (LIB / 'template.html').read_text()
    html = html.replace('__SCENES_JS__', (LIB / 'core.js').read_text() + '\n' + (R / 'scripts/episode.js').read_text())
    # timeline.json 不带 logo 键（保持旧格式）；index.html 内嵌的数据单独加一份带 logo 的副本
    html_data = dict(data, logo=bool(logo))
    (out / 'index.html').write_text(html.replace('__DATA__', json.dumps(html_data, ensure_ascii=False)).replace('__DURATION__', str(duration)))
    progress.update(R.parent, R.name, '程序动画', f'✅ {datetime.date.today().isoformat()}')
    print(json.dumps(dict(duration=round(duration, 2), scenes=len(scenes), captions=len(caps), logo=bool(logo))))
    print('下一步请自己跑一遍 check：cd', R.name, '&& npx hyperframes@0.8.20 check comp', file=sys.stderr)


if __name__ == '__main__':
    main()
