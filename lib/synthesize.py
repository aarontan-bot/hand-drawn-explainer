"""把一集里缺配音的旁白合成语音。每段旁白只发起一次授权请求，绝不自动重试。

用法：python3 synthesize.py <集目录> [shot-NN ...]
  不传 shot 就合成该集 audio/ 下所有还缺 mp3 的 shot-*.txt。
音色取值顺序：--speaker 参数 > 环境变量 TTS_SPEAKER > <集目录>/../series.json 的 speaker 字段 > lib/defaults.json 的 speaker。
密钥读取顺序：环境变量 VOLCENGINE_TTS_API_KEY，否则读密钥文件（默认 ~/.config/nikola-video/volcengine-tts.key，
可用环境变量 VOLCENGINE_TTS_KEY_FILE 覆盖路径）。
合成成功后立刻用返回的词时间戳与原文比对；对不上（通常是被截断）就把 meta 标 truncated，报错退出码 2，不删文件。
"""
import argparse, base64, datetime, hashlib, json, os, re, sys, urllib.error, urllib.request, uuid
from pathlib import Path

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB))
import progress

N = lambda s: re.sub(r'\W+', '', s).lower()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def resolve_speaker(cli_speaker, episode_dir):
    """--speaker > 环境变量 TTS_SPEAKER > series.json 的 speaker 字段 > lib/defaults.json 的 speaker；
    lib/defaults.json 缺省是空字符串（内核不内置任何具体音色），四级都取不到就清楚地报错退出，不猜。"""
    if cli_speaker:
        return cli_speaker
    if os.environ.get('TTS_SPEAKER'):
        return os.environ['TTS_SPEAKER']
    series_json = episode_dir.parent / 'series.json'
    if series_json.exists():
        try:
            v = json.loads(series_json.read_text(encoding='utf-8')).get('speaker')
            if v:
                return v
        except (json.JSONDecodeError, OSError):
            pass
    v = json.loads((LIB / 'defaults.json').read_text(encoding='utf-8')).get('speaker')
    if v:
        return v
    print('错误：未指定音色：请在 series.json 或 --speaker 指定', file=sys.stderr)
    sys.exit(2)


def resolve_key():
    key = os.environ.get('VOLCENGINE_TTS_API_KEY')
    if key:
        return key
    key_file = Path(os.environ.get('VOLCENGINE_TTS_KEY_FILE') or (Path.home() / '.config/nikola-video/volcengine-tts.key'))
    return key_file.read_text().strip()


def check_truncation(name, events, text):
    words = [w for e in events if e.get('sentence') for w in e['sentence']['words']]
    joined = ''.join(w['word'] for w in words)
    nj, nt = N(joined), N(text)
    return nj == nt, joined


def synth_one(episode_dir, name, speaker, resource, key):
    src = episode_dir / f'audio/{name}.txt'
    out = src.with_suffix('.mp3'); meta = out.with_suffix('.mp3.json')
    txt = src.read_text().strip()
    assert 0 < len(txt) <= 1500
    body = {'user': {'uid': 'local-video'}, 'req_params': {'text': txt, 'speaker': speaker, 'audio_params': {'format': 'mp3', 'sample_rate': 24000, 'enable_subtitle': True}}}
    b = json.dumps(body, ensure_ascii=False).encode(); digest = sha(b)
    if out.exists():
        m = json.loads(meta.read_text())
        assert m['complete'] and m['request_sha256'] == digest and m['audio_sha256'] == sha(out.read_bytes())
        print('Verified cache', name)
        return
    if meta.exists():
        old = json.loads(meta.read_text())
        if old.get('error') and not out.exists():
            # 上次请求以网络错误（如 read timeout）收场、没有产出音频：视为未发生，清掉再发一次
            print(f'{name}: 上次请求失败（{old["error"][:60]}），清掉残留元数据后重试', flush=True)
            meta.unlink()
        else:
            raise SystemExit(f'{name}: 有未处理完的旧请求（meta 无 error 或已有音频），先检查 meta 文件再重试')
    rid = str(uuid.uuid4())
    m = {'request_id': rid, 'request_sha256': digest, 'complete': False, 'speaker': speaker, 'characters': len(txt)}
    meta.write_text(json.dumps(m, indent=2)); print('Request', name, 'chars', len(txt), 'id', rid, flush=True)
    h = {'X-Api-Key': key, 'X-Api-Resource-Id': resource, 'X-Api-Request-Id': rid, 'Content-Type': 'application/json'}
    r = urllib.request.Request('https://openspeech.bytedance.com/api/v3/tts/unidirectional', data=b, headers=h)
    chunks, events = [], []
    try:
        with urllib.request.urlopen(r, timeout=180) as response:
            for line in response:
                if not line.strip():
                    continue
                e = json.loads(line); data = e.pop('data', None); events.append(e)
                if e.get('code') not in (0, 20000000):
                    raise ValueError('Service code ' + str(e.get('code')) + ': ' + str(e.get('message', '')))
                if data:
                    chunks.append(base64.b64decode(data))
                if e.get('code') == 20000000:
                    m['complete'] = True
    except Exception as ex:
        m['error'] = str(ex).replace(key, '[REDACTED]'); meta.write_text(json.dumps(m, ensure_ascii=False, indent=2))
        print('错误：', m['error']); sys.exit(1)
    raw = b''.join(chunks)
    assert m['complete'] and raw
    with out.open('xb') as f:
        f.write(raw)
    m.update(audio_sha256=sha(raw), events=events)
    ok, joined = check_truncation(name, events, txt)
    if not ok:
        m['truncated'] = True
        meta.write_text(json.dumps(m, ensure_ascii=False, indent=2))
        nj, nt = N(joined), N(txt)
        k = 0
        while k < len(nj) and k < len(nt) and nj[k] == nt[k]:
            k += 1
        print(f'错误：{name} 配音文字与旁白原文不一致（按去标点、忽略大小写比对）。', file=sys.stderr)
        print(f'  合成到「…{nj[max(0, len(nj) - 20):]}」为止', file=sys.stderr)
        print(f'  原文剩余「{nt[k:k + 20]}…」', file=sys.stderr)
        print('  配音被截断：改措辞后删除该镜 mp3 与 mp3.json 重合成', file=sys.stderr)
        sys.exit(2)
    meta.write_text(json.dumps(m, ensure_ascii=False, indent=2))
    print('Saved', out.name, 'bytes', len(raw), 'event keys', sorted(set(k for e in events for k in e)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('episode_dir')
    ap.add_argument('shots', nargs='*', help='shot-NN ...；不传就合成所有缺 mp3 的')
    ap.add_argument('--speaker', default=None)
    args = ap.parse_args()
    episode_dir = Path(args.episode_dir).resolve()
    speaker = resolve_speaker(args.speaker, episode_dir)
    resource = json.loads((LIB / 'defaults.json').read_text(encoding='utf-8'))['tts_resource']

    if args.shots:
        names = args.shots
    else:
        names = sorted(p.stem for p in (episode_dir / 'audio').glob('shot-*.txt') if not p.with_suffix('.mp3').exists())
        if not names:
            print('没有缺配音的镜头。')

    if names:
        key = resolve_key()
        for name in names:
            synth_one(episode_dir, name, speaker, resource, key)

    all_txt = sorted(p.stem for p in (episode_dir / 'audio').glob('shot-*.txt'))
    if all_txt and all(episode_dir.joinpath(f'audio/{n}.mp3').exists() for n in all_txt):
        progress.update(episode_dir.parent, episode_dir.name, '配音', f'✅ {datetime.date.today().isoformat()}')


if __name__ == '__main__':
    main()
