"""把一批脚本 md 生成一个可逐集审阅的 HTML 阅读版。

用法：python3 build_reader.py <脚本目录> [输出html]
  默认匹配目录下除 00- 开头外的所有 *.md，按文件名排序；不传输出路径就写到该目录 脚本审阅版.html
"""
import json, sys
from pathlib import Path

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB))
import script_md

ROOT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else ROOT / '脚本审阅版.html'

eps = []
card_keys = []  # 记录出现过的卡片字段，保持首次出现的顺序
for f in script_md.iter_script_files(ROOT):
    sc = script_md.parse(f)
    for k in sc.card_keys:
        if k not in card_keys:
            card_keys.append(k)
    shots = []
    for s in sc.shots:
        d = {'no': s.no_raw, 't': s.span, 'kind': s.method}
        d.update(s.fields)
        shots.append(d)
    eps.append({'file': f.name, 'title': sc.title, 'card': sc.card, 'shots': shots})

data = json.dumps(eps, ensure_ascii=False)
keys_js = json.dumps(card_keys, ensure_ascii=False)
page = """<!doctype html><html lang="zh"><meta charset="utf-8"><title>脚本审阅</title>
<style>
:root{--bg:#f6f3ec;--ink:#1f1d1a;--mute:#6f6a60;--line:#e2ddd2;--card:#fffdf8;--hand:#2f6fdb;--prog:#2e8b57;--hl:#fff3a3}
*{box-sizing:border-box}body{margin:0;font:15px/1.7 -apple-system,"PingFang SC",sans-serif;background:var(--bg);color:var(--ink);display:flex;height:100vh}
nav{width:250px;flex:none;border-right:1px solid var(--line);padding:18px 12px;overflow:auto}
nav h1{font-size:15px;margin:0 8px 12px}nav button{display:block;width:100%;text-align:left;border:0;background:none;padding:9px 10px;border-radius:8px;font:inherit;color:var(--ink);cursor:pointer}
nav button.on{background:var(--ink);color:#fff}nav small{display:block;color:var(--mute);font-size:12px}nav button.on small{color:#ccc}
main{flex:1;overflow:auto;padding:28px 40px 80px}h2{margin:0 0 14px;font-size:24px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 18px;margin-bottom:22px}
.card div{display:grid;grid-template-columns:90px 1fr;gap:10px;padding:4px 0}.card b{color:var(--mute);font-weight:500}
.filter{margin:0 0 14px;display:flex;gap:8px}.filter button{border:1px solid var(--line);background:var(--card);border-radius:20px;padding:4px 14px;font:inherit;cursor:pointer}.filter button.on{background:var(--ink);color:#fff}
.shot{display:grid;grid-template-columns:96px 1fr;gap:16px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 18px;margin-bottom:10px}
.meta{font-size:13px;color:var(--mute)}.meta strong{display:block;font-size:17px;color:var(--ink)}
.tag{display:inline-block;margin-top:6px;padding:1px 8px;border-radius:10px;color:#fff;font-size:12px}.插画{background:var(--hand)}.程序{background:var(--prog)}
.nar{font-size:16px}.nar.none{color:var(--mute)}.row{margin-top:8px;font-size:13.5px;color:#4a463f}.row b{color:var(--mute);font-weight:500;margin-right:6px}
.scr{background:var(--hl);padding:2px 6px;border-radius:4px;white-space:pre-wrap}
</style>
<nav><h1>脚本审阅</h1><div id="nav"></div></nav><main id="main"></main>
<script>
const E=__DATA__;const CARD_KEYS=__KEYS__;let cur=0,flt='全部';
const esc=s=>(s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function nav(){document.getElementById('nav').innerHTML=E.map((e,i)=>`<button class="${i==cur?'on':''}" onclick="cur=${i};draw()">${esc(e.title)}<small>${esc((e.card['时长']||'').replace(/ ｜.*/,''))}</small></button>`).join('')}
function draw(){nav();const e=E[cur];const c=e.card;
 const keys=CARD_KEYS;
 const shots=e.shots.filter(s=>flt=='全部'||s.kind==flt);
 document.getElementById('main').innerHTML=`<h2>${esc(e.title)}</h2>
 <div class="card">${keys.filter(k=>c[k]).map(k=>`<div><b>${k}</b><span>${esc(c[k])}</span></div>`).join('')}</div>
 <div class="filter">${['全部','插画','程序'].map(k=>`<button class="${k==flt?'on':''}" onclick="flt='${k}';draw()">${k}</button>`).join('')}<span class="meta" style="align-self:center">共 ${e.shots.length} 镜</span></div>
 ${shots.map(s=>{const n=s['旁白']||'';const none=n.startsWith('（无');
  return `<div class="shot"><div class="meta"><strong>镜 ${esc(s.no.replace('镜 ',''))}</strong>${esc(s.t)}<br><span class="tag ${s.kind}">${s.kind}</span></div>
  <div><div class="nar ${none?'none':''}">${esc(n)}</div>
  ${s['停顿']?`<div class="row"><b>停顿</b>${esc(s['停顿'])}</div>`:''}
  <div class="row"><b>画面</b>${esc(s['画面'])}</div>
  ${s['屏幕文字']?`<div class="row"><b>屏幕文字</b><span class="scr">${esc(s['屏幕文字'].replace(/^- /gm,''))}</span></div>`:''}</div></div>`}).join('')}`;
 document.getElementById('main').scrollTop=0}
draw();
</script></html>"""
OUT.write_text(page.replace('__DATA__', data).replace('__KEYS__', keys_js), encoding='utf-8')
print(OUT, sum(len(e['shots']) for e in eps), '镜')
