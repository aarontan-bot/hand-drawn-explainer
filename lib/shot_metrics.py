#!/usr/bin/env python3
"""每镜「画完」时刻的 ELI5 量化判据（大图少字 / 安全区 / 彩色数）。

用法：
  单集：  python3 shot_metrics.py <集目录> [--json]
  基线：  python3 shot_metrics.py --baseline <系列目录> [<系列目录> ...]
          （对每个系列目录下所有 第*集 子目录逐集跑一遍，汇总打印各指标 P50/P90/max 与建议阈值）

「画完」时刻取 03-production.md §4 的公式：
  min(end-0.5, max(events.values())+1.8)，无 events 则 start+2.5
逐镜：复制 comp/index.html 到 /tmp（文件名带 PID，避免并发冲突），注入脚本 seek 到该时刻
并在 DOM 里量出 5 个指标（写进 document.title 的 JSON），用 headless Chrome --dump-dom 取回。
常驻层（Logo 角标 .brand、集数条 .series、字幕条 .capbar、进度条 .progress、字幕文字 .caption，
均见 lib/template.html）与插画整幅背景 .art/.half（本来就设计成在 Logo/字幕条下方出血，
见 references/02-script.md「构图」一节）排除在「安全区出界」判据之外，但 .art/.half 仍计入
「主图高度」候选（插画镜的主图就是它）。
单镜跑不动（Chrome 超时/出错）不让整集失败，改记一行错误。
"""
import argparse
import html as html_mod
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

LIB = Path(__file__).resolve().parent
CHROME = os.environ.get('CHROME', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
THRESHOLDS = json.loads((LIB / 'metrics_thresholds.json').read_text(encoding='utf-8'))
TIMEOUT_SEC = 25

# 常驻层选择器：来自 lib/template.html（.brand Logo 角标 / .series 集数条 / .capbar 字幕条背景 /
# .progress 进度条 / .caption 字幕文字）。.art/.half 是插画整幅背景（core.js Scene.art()），
# 设计上就会延伸到安全区外（Logo、字幕条盖在它上面），所以也从「安全区出界」里排除（2026-09-18
# 拍板保留），但仍计入「主图高度」候选（插画镜的主图就是它）。
# note() 的标签角标（core.js note() 里 size:30/weight:600/anchor:start 那个 <text>，没有 class）
# 也从「最小字号」判据里排除，只按正文判 40px——签名识别写在 JS_TEMPLATE 的 isNoteTag() 里。
JS_TEMPLATE = r"""
;(function(){
  window.__timelines.main.seek(__T__);
  var main=document.getElementById('main');
  var mRect=main.getBoundingClientRect();
  var k= mRect.width ? 1920/mRect.width : 1;
  function toBox(rect){return {y:(rect.top-mRect.top)*k, h:rect.height*k}}
  function opacityOf(el){
    var v=1, n=el;
    while(n && n.nodeType===1){
      var cs=getComputedStyle(n);
      if(cs.display==='none'||cs.visibility==='hidden') return 0;
      v*=parseFloat(cs.opacity);
      n=n.parentElement;
    }
    return v;
  }
  var CHROME_SEL=['.brand','.series','.capbar','.progress','.caption'];
  function isChromeEl(el){return CHROME_SEL.some(function(s){return el.closest(s)})}
  function textChars(s){return (s||'').replace(/\s+/g,'').length}
  // core.js 的 note() 给标签角标写死了 size:30/weight:600/anchor:start（core.js 第 52 行 note()），
  // 且这个 <text> 没有 class 可选；不改 core.js 的前提下，用这个签名识别它，min_font 排除它，
  // 只按正文判 40px。core.js 这段实现要是改了签名，这里要跟着改。
  function isNoteTag(t){
    if(t.tagName.toLowerCase()!=='text') return false;
    var cs=getComputedStyle(t);
    return Math.abs(parseFloat(cs.fontSize)-30)<0.5 && parseInt(cs.fontWeight,10)===600 && t.getAttribute('text-anchor')==='start';
  }
  function pushColor(hex, hues){
    hex=(hex||'').trim().toLowerCase();
    var m=hex.match(/^#([0-9a-f]{6})$/);
    if(!m) return;
    var r=parseInt(m[1].slice(0,2),16)/255, g=parseInt(m[1].slice(2,4),16)/255, b=parseInt(m[1].slice(4,6),16)/255;
    var mx=Math.max(r,g,b), mn=Math.min(r,g,b), l=(mx+mn)/2, s=0, hdeg=0;
    if(mx!==mn){
      var d=mx-mn; s=l>0.5? d/(2-mx-mn): d/(mx+mn);
      if(mx===r) hdeg=(g-b)/d+(g<b?6:0); else if(mx===g) hdeg=(b-r)/d+2; else hdeg=(r-g)/d+4;
      hdeg*=60;
    }
    if(s<0.15) return; // 去掉黑白灰
    hues[Math.floor(((hdeg%360)+360)%360/30)]=true;
  }

  var scene=null;
  document.querySelectorAll('.scene').forEach(function(s){if(getComputedStyle(s).visibility==='visible') scene=s});
  var chars=0, minFont=Infinity, outSafe=0, heroH=0, hues={};

  if(scene){
    var svg=scene.querySelector('svg.stage');
    if(svg){
      Array.prototype.forEach.call(svg.children, function(node){
        if(isChromeEl(node)) return;
        if(opacityOf(node)<=0.05) return;
        var rect=node.getBoundingClientRect();
        if(!rect.width||!rect.height) return;
        var box=toBox(rect);
        var outside = box.y<130 || (box.y+box.h)>860;
        if(node.tagName.toLowerCase()==='text'){
          if(outside) outSafe++;
          chars+=textChars(node.textContent);
          var fs=parseFloat(getComputedStyle(node).fontSize); if(fs && !isNoteTag(node) && fs<minFont) minFont=fs;
        } else {
          if(outside) outSafe++;
          if(box.h>heroH) heroH=box.h;
          node.querySelectorAll('text').forEach(function(t){
            if(opacityOf(t)<=0.05) return;
            chars+=textChars(t.textContent);
            var fs=parseFloat(getComputedStyle(t).fontSize); if(fs && !isNoteTag(t) && fs<minFont) minFont=fs;
          });
          node.querySelectorAll('[stroke],[fill]').forEach(function(sh){
            pushColor(sh.getAttribute('stroke'), hues); pushColor(sh.getAttribute('fill'), hues);
          });
          pushColor(node.getAttribute('stroke'), hues); pushColor(node.getAttribute('fill'), hues);
        }
      });
    }
    scene.querySelectorAll('div.h, div.note, div.pill').forEach(function(d){
      if(isChromeEl(d)) return;
      if(opacityOf(d)<=0.05) return;
      var rect=d.getBoundingClientRect();
      if(!rect.width||!rect.height) return;
      var box=toBox(rect);
      if(box.y<130 || (box.y+box.h)>860) outSafe++;
      chars+=textChars(d.textContent);
      var fs=parseFloat(getComputedStyle(d).fontSize); if(fs && fs<minFont) minFont=fs;
    });
    scene.querySelectorAll('.art .half').forEach(function(h){
      if(opacityOf(h)<=0.05) return;
      var rect=h.getBoundingClientRect();
      if(!rect.width||!rect.height) return;
      var box=toBox(rect);
      if(box.h>heroH) heroH=box.h; // .art 不计入 outSafe：整幅出血是设计如此
    });
  }
  if(!isFinite(minFont)) minFont=null;
  document.title=JSON.stringify({chars:chars,min_font:minFont,out_of_safe:outSafe,hero_h:Math.round(heroH),colors:Object.keys(hues).length});
})();
"""


def shot_moment(scene):
    events = scene.get('events') or {}
    if events:
        return min(scene['end'] - 0.5, max(events.values()) + 1.8)
    return scene['start'] + 2.5


def measure_one(comp_dir, t, tag):
    """复制 comp/index.html，注入 seek + 量测脚本，headless Chrome --dump-dom 取回 document.title。"""
    src = comp_dir / 'index.html'
    tmp = comp_dir / f'_metrics_{os.getpid()}_{tag}.html'
    dump = comp_dir / f'_metrics_{os.getpid()}_{tag}.dump.html'
    try:
        html = src.read_text(encoding='utf-8')
        inject = JS_TEMPLATE.replace('__T__', repr(float(t)))
        marker = '</script></body></html>'
        if marker not in html:
            return {'error': 'index.html 里找不到注入点 </script></body></html>'}
        html = html.replace(marker, inject + marker)
        tmp.write_text(html, encoding='utf-8')
        cmd = [CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars',
               '--window-size=1920,1080', '--virtual-time-budget=4000',
               f'--dump-dom', f'file://{tmp}']
        r = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT_SEC)
        dumped = r.stdout.decode('utf-8', 'ignore')
        m = re.search(r'<title>(.*?)</title>', dumped, re.S)
        if not m:
            return {'error': f'Chrome 没输出可解析的 <title>（stderr: {r.stderr.decode("utf-8","ignore")[:200]}）'}
        data = json.loads(html_mod.unescape(m.group(1)))
        return data
    except subprocess.TimeoutExpired:
        return {'error': f'Chrome 超时（>{TIMEOUT_SEC}s）'}
    except Exception as e:
        return {'error': f'{type(e).__name__}: {e}'}
    finally:
        tmp.unlink(missing_ok=True)
        dump.unlink(missing_ok=True)


def mark_row(kind, d):
    marks = []
    if 'error' in d:
        return '错误'
    if d.get('out_of_safe', 0) > 0:
        marks.append('高:出安全区')
    chars_max = THRESHOLDS.get('chars_max')
    if chars_max is not None and d.get('chars', 0) > chars_max:
        marks.append('中:字数超阈值')
    if d.get('min_font') is not None and d['min_font'] < THRESHOLDS.get('min_font', 40):
        marks.append('中:字号偏小')
    hero_ratio = (d.get('hero_h', 0) or 0) / 730
    if hero_ratio and hero_ratio < THRESHOLDS.get('hero_ratio_min', 0.33):
        marks.append('低:主图不够大')
    if d.get('colors', 0) > THRESHOLDS.get('colors_max', 2):
        marks.append('低:彩色过多')
    return '；'.join(marks) if marks else '—'


def run_episode(ep_dir):
    """对一集的每个镜头量测，返回 [{no,kind,t,...metrics,mark}]。"""
    # 必须绝对化：measure_one 用 f'file://{tmp}' 拼 URL，相对的集目录会生成非法 file://，
    # Chrome 打不开，<title> 里拿不到量测 JSON，逐镜报 JSONDecodeError（peek.sh 同款坑）
    ep_dir = Path(ep_dir).resolve()
    timeline = json.loads((ep_dir / 'timeline.json').read_text(encoding='utf-8'))
    comp_dir = ep_dir / 'comp'
    rows = []
    for s in timeline['scenes']:
        t = round(shot_moment(s), 2)
        d = measure_one(comp_dir, t, f"{ep_dir.name}_{s['no']}")
        row = dict(no=s['no'], kind=s['kind'], t=t)
        row.update(d)
        row['mark'] = mark_row(s['kind'], d)
        rows.append(row)
    return rows


def print_table(rows):
    print('| 镜 | kind | 时刻 | 字数 | 最小字号 | 出安全区 | 主图高/占比 | 彩色数 | 标记 |')
    print('|---|---|---|---|---|---|---|---|---|')
    for r in rows:
        if 'error' in r:
            print(f"| {r['no']} | {r['kind']} | {r['t']} | - | - | - | - | - | 错误：{r['error']} |")
            continue
        hero_h = r.get('hero_h', 0) or 0
        ratio = round(hero_h / 730, 2)
        min_font = r.get('min_font')
        min_font_s = '-' if min_font is None else round(min_font, 1)
        print(f"| {r['no']} | {r['kind']} | {r['t']} | {r.get('chars', 0)} | {min_font_s} | {r.get('out_of_safe', 0)} | {hero_h}/{ratio} | {r.get('colors', 0)} | {r['mark']} |")


def percentile(values, p):
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * p
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] + (s[c] - s[f]) * (k - f)


def run_baseline(series_dirs):
    all_rows = []
    for sd in series_dirs:
        sd = Path(sd)
        for ep in sorted(sd.glob('第*集')):
            if not (ep / 'timeline.json').exists() or not (ep / 'comp/index.html').exists():
                continue
            print(f'# {ep}', file=sys.stderr)
            rows = run_episode(ep)
            for r in rows:
                r['episode'] = str(ep)
            all_rows.extend(rows)
    ok = [r for r in all_rows if 'error' not in r]
    err = [r for r in all_rows if 'error' in r]
    print(f'共 {len(all_rows)} 镜，成功 {len(ok)}，出错 {len(err)}\n')
    for r in err:
        print(f"错误：{r['episode']} 第{r['no']}镜：{r['error']}")
    for key, label in (('chars', '字数'), ('min_font', '最小字号'), ('hero_h', '主图高'), ('colors', '彩色数'), ('out_of_safe', '出安全区')):
        vals = [r[key] for r in ok if r.get(key) is not None]
        if not vals:
            continue
        p50, p90, mx = percentile(vals, .5), percentile(vals, .9), max(vals)
        line = f'{label}：P50={p50:.1f} P90={p90:.1f} max={mx:.1f}'
        if key == 'chars':
            line += f'（建议 chars_max = {math.ceil(p90 / 5) * 5}）'
        print(line)
    return all_rows


def main():
    ap = argparse.ArgumentParser(description='每镜「画完」时刻的 ELI5 量化判据')
    ap.add_argument('episode_dir', nargs='?', help='集目录（单集模式）')
    ap.add_argument('--json', action='store_true', help='额外输出 JSON')
    ap.add_argument('--baseline', nargs='+', metavar='系列目录', help='对系列目录下所有 第*集 跑一遍，输出分布与建议阈值')
    args = ap.parse_args()

    if args.baseline:
        run_baseline(args.baseline)
        return

    if not args.episode_dir:
        ap.error('需要给出集目录，或用 --baseline 系列目录')

    rows = run_episode(args.episode_dir)
    print_table(rows)
    if args.json:
        print()
        print(json.dumps(rows, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
