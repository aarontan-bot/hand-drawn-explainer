"""把一集打成单文件、离线可开的预审包 HTML：给审片人逐镜勾选用。

用法：python3 preview_pack.py <集目录> <输出html> [--md <脚本md>] [--title 文本]
  --md 给了才有「屏幕文字」「做法」文案；不给就先用 Project（从集目录往上找 series.json）自己找，
       真找不到才退化成 timeline.json + audio 旁白 + 插画兜底并警告。
  --title 缺省取 scripts/episode.js 的 EP.title。
图片 base64 内嵌、等比缩到宽 960。每镜一块：镜号 + 做法 + 时间段 + 旁白全文 + 屏幕文字 + 插画，
每一项旁边一个复选框 + 一个备注框；底部按钮把勾选状态导出成可复制文本。

统计里的「旁白总字数」是去标点空白的计数（script_md.narration_chars），与本集卡片的
「旁白字数」、retime.py 的回填同源——此前这里只去空白、把标点也算成字，两个数对不上。
"""
import argparse, base64, io, json, re, sys
from pathlib import Path

from PIL import Image

LIB = Path(__file__).resolve().parent
sys.path.insert(0, str(LIB))
import script_md
import project as project_mod
from project import Project

PREVIEW_W = 960


def parse_episode_js(ep_dir):
    js_path = ep_dir / 'scripts/episode.js'
    if not js_path.exists():
        return None, None
    js = js_path.read_text(encoding='utf-8')
    m = re.search(r'const\s+EP\s*=\s*\{(.*?)\}\s*;', js)
    if not m:
        return None, None
    body = m.group(1)
    no_m = re.search(r'no\s*:\s*(\d+)', body)
    title_m = re.search(r"title\s*:\s*['\"]((?:[^'\"\\]|\\.)*)['\"]", body)
    return (int(no_m.group(1)) if no_m else None), (title_m.group(1) if title_m else None)


def resolve_md(ep_dir, md_arg):
    """--md 没给就用 Project 自己找；真找不到才退化并警告。提示走 stderr（stdout 是那行 JSON）。"""
    if md_arg:
        return Path(md_arg).resolve()
    proj = Project.from_episode_dir(ep_dir)
    no = project_mod.episode_no_of(ep_dir)
    md = proj.script_for(no) if (proj and no is not None) else None
    if md:
        print(f'提示：未给 --md，自动用 {md}', file=sys.stderr)
        return md
    print('警告：未给 --md 且没能自动找到脚本 md，预审包里屏幕文字将是 0 条', file=sys.stderr)
    return None


def fmt_ts(sec):
    sec = int(round(sec))
    return f'{sec // 60:02}:{sec % 60:02}'


def img_data_uri(png_path, max_w=PREVIEW_W):
    im = Image.open(png_path).convert('RGB')
    if im.width > max_w:
        ratio = max_w / im.width
        im = im.resize((max_w, max(1, round(im.height * ratio))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format='JPEG', quality=85)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


def default_kind_label(scene_kind):
    if scene_kind in ('illus', 'single'):
        return '插画'
    if scene_kind == 'title':
        return '片头'
    if scene_kind == 'end':
        return '片尾'
    return '程序'


def build_shots(ep_dir, timeline, md_shots):
    illus_count = program_count = screen_text_count = narration_chars = 0
    out = []
    for scene in timeline['scenes']:
        no, kind = scene['no'], scene['kind']
        md = (md_shots or {}).get(no)
        kind_label = (md.method if md else '') or default_kind_label(kind)

        txt_path = ep_dir / f'audio/shot-{no:02}.txt'
        narration = txt_path.read_text(encoding='utf-8').strip() if txt_path.exists() else (md.narration if md else '')
        narration_chars += script_md.narration_chars(narration)

        screen_lines = md.screen_items(strip_circled=True) if md else []
        screen_text_count += len(screen_lines)

        illus_uri = None
        if kind in ('illus', 'single'):
            illus_count += 1
            png = ep_dir / f'illus/{no:02}.png'
            if png.exists():
                illus_uri = img_data_uri(png)
        else:
            program_count += 1

        out.append(dict(
            no=no, kind_label=kind_label,
            time=f"{fmt_ts(scene['start'])}–{fmt_ts(scene['end'])}",
            narration=narration, screen_lines=screen_lines, illus=illus_uri,
        ))
    stats = dict(illus=illus_count, program=program_count, screen=screen_text_count, chars=narration_chars)
    return out, stats


PAGE = """<!doctype html><html lang="zh"><meta charset="utf-8"><title>预审包</title>
<style>
:root{--bg:#f6f3ec;--ink:#1f1d1a;--mute:#6f6a60;--line:#e2ddd2;--card:#fffdf8;--hl:#fff3a3}
*{box-sizing:border-box}body{margin:0;font:15px/1.7 -apple-system,"PingFang SC",sans-serif;background:var(--bg);color:var(--ink)}
header{padding:28px 40px;border-bottom:1px solid var(--line);background:var(--card)}
header h1{margin:0 0 6px;font-size:26px}header .sub{color:var(--mute);font-size:14px}
.stats{display:flex;gap:22px;margin-top:14px;flex-wrap:wrap}
.stat{background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:8px 16px;font-size:14px}
.stat b{font-size:18px;margin-right:4px}
main{padding:24px 40px 100px;max-width:980px;margin:0 auto}
.shot{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 22px;margin-bottom:18px}
.shot .head{display:flex;align-items:baseline;gap:12px;margin-bottom:10px}
.shot .head strong{font-size:19px}
.tag{display:inline-block;padding:1px 10px;border-radius:10px;background:var(--ink);color:#fff;font-size:12px}
.time{color:var(--mute);font-size:13px}
.item{display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-top:1px dashed var(--line)}
.item:first-of-type{border-top:none}
.item input[type=checkbox]{margin-top:4px;width:16px;height:16px;flex:none}
.item .body{flex:1}
.item .label{color:var(--mute);font-size:12px;margin-bottom:2px}
.item .val{white-space:pre-wrap}
.item .val.scr{background:var(--hl);display:inline-block;padding:2px 6px;border-radius:4px}
.item .note{width:100%;margin-top:6px;border:1px solid var(--line);border-radius:6px;padding:4px 8px;font:inherit;resize:vertical}
.item img{max-width:100%;border-radius:8px;border:1px solid var(--line);display:block;margin-top:4px}
footer{position:sticky;bottom:0;background:var(--card);border-top:1px solid var(--line);padding:14px 40px;display:flex;gap:12px;align-items:center}
footer button{font:inherit;padding:8px 18px;border-radius:20px;border:1px solid var(--ink);background:var(--ink);color:#fff;cursor:pointer}
#exportBox{width:100%;max-width:980px;margin:0 auto;padding:0 40px 40px}
#exportBox textarea{width:100%;height:180px;font:13px/1.5 ui-monospace,monospace;padding:10px;border:1px solid var(--line);border-radius:8px}
@media print{
  footer,#exportBox{display:none}
  body{-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .item input[type=checkbox]{-webkit-appearance:checkbox;opacity:1}
  .shot{break-inside:avoid}
}
</style>
<header>
  <h1 id="title"></h1>
  <div class="sub" id="subline"></div>
  <div class="stats" id="stats"></div>
</header>
<main id="main"></main>
<div id="exportBox" style="display:none"><textarea id="exportText" readonly></textarea></div>
<footer>
  <button onclick="doExport()">全部勾选后可导出</button>
  <span id="exportHint" style="color:var(--mute);font-size:13px"></span>
</footer>
<script>
const SHOTS = __SHOTS__;
const META = __META__;

function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}

function itemHtml(shotNo, key, label, valueHtml){
  const id = `c_${shotNo}_${key}`;
  return `<div class="item">
    <input type="checkbox" id="${id}">
    <div class="body">
      <div class="label">${esc(label)}</div>
      <div class="val">${valueHtml}</div>
      <textarea class="note" placeholder="备注" data-shot="${shotNo}" data-item="${esc(label)}"></textarea>
    </div>
  </div>`;
}

function draw(){
  document.getElementById('title').textContent = META.title;
  document.getElementById('subline').textContent = `第 ${META.no ?? '?'} 集`;
  document.getElementById('stats').innerHTML = [
    ['插画', META.stats.illus, '张'],
    ['程序镜', META.stats.program, '个'],
    ['屏幕文字', META.stats.screen, '条'],
    ['旁白总字数', META.stats.chars, '字'],
  ].map(([k,v,u])=>`<div class="stat"><b>${v}</b>${esc(k)}（${u}）</div>`).join('');

  document.getElementById('main').innerHTML = SHOTS.map(s=>{
    let items = '';
    items += itemHtml(s.no, 'nar', '旁白', `<span class="val">${esc(s.narration) || '（无）'}</span>`);
    s.screen_lines.forEach((line,i)=>{
      items += itemHtml(s.no, `scr${i}`, `屏幕文字 ${i+1}`, `<span class="scr">${esc(line)}</span>`);
    });
    if(s.illus){
      items += itemHtml(s.no, 'illus', '插画', `<img src="${s.illus}">`);
    }
    return `<section class="shot">
      <div class="head"><strong>镜 ${String(s.no).padStart(2,'0')}</strong><span class="tag">${esc(s.kind_label)}</span><span class="time">${esc(s.time)}</span></div>
      ${items}
    </section>`;
  }).join('');
}

function doExport(){
  const lines = [];
  document.querySelectorAll('.item').forEach(item=>{
    const cb = item.querySelector('input[type=checkbox]');
    const label = item.querySelector('.label').textContent;
    const note = item.querySelector('.note').value.trim();
    const shot = item.querySelector('.note').dataset.shot;
    lines.push(`镜${String(shot).padStart(2,'0')} / ${label} / ${cb.checked ? '✓' : '未勾'} / ${note}`);
  });
  document.getElementById('exportBox').style.display = 'block';
  document.getElementById('exportText').value = lines.join('\\n');
  document.getElementById('exportText').select();
  document.getElementById('exportHint').textContent = '已生成，可全选复制';
}

draw();
</script>
</html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ep_dir')
    ap.add_argument('out_html')
    ap.add_argument('--md')
    ap.add_argument('--title')
    args = ap.parse_args()

    ep_dir = Path(args.ep_dir).resolve()
    timeline = json.loads((ep_dir / 'timeline.json').read_text())
    md_path = resolve_md(ep_dir, args.md)
    md_shots = script_md.parse(md_path).shots_by_no if md_path else None
    js_no, js_title = parse_episode_js(ep_dir)

    shots, stats = build_shots(ep_dir, timeline, md_shots)
    title = args.title or js_title or ep_dir.name
    meta = dict(title=title, no=js_no, stats=stats)

    html = PAGE.replace('__SHOTS__', json.dumps(shots, ensure_ascii=False)).replace('__META__', json.dumps(meta, ensure_ascii=False))
    out = Path(args.out_html).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding='utf-8')
    print(json.dumps(dict(out=str(out), size=out.stat().st_size, shots=len(shots), **stats), ensure_ascii=False))


if __name__ == '__main__':
    main()
