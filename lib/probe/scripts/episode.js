// 探针：一页渲出 core.js 全部图标、角色道具、纸条标注与金句样式，确认共用层在本机渲染正常。
// 新系列第一次派单前，或 core.js 有改动时，先跑 probe.sh 看这张总览图，再派子代理。
const EP = {no: 0, title: '探针', sub: ''};

// core.js sc.icon(kind,...) 的全部 kind（从 core.js 的 icon() 里逐个摘出，别漏）
const ICON_KINDS = ['question', 'command', 'page', 'cards', 'sketch', 'form', 'house', 'flag', 'eye', 'think',
 'book', 'lens', 'brush', 'fork', 'ruler', 'plus', 'target', 'people', 'stop', 'list', 'table', 'paras',
 'diary', 'scroll', 'news', 'medal', 'cake', 'clock', 'hand', 'star', 'bulb', 'chat', 'photo', 'gear',
 'loop', 'lock', 'key', 'shelf'];

Object.assign(BUILD, {
 // 38 个图标铺成 8x5 网格，逐个 pop 入场，下面用 sc.text 标 kind 名字。
 probe_icons(sc, s) {
  const t0 = sc.t0, cols = 8, cellW = 1920 / cols, top = 190, cellH = (860 - top) / 5;
  const title = sc.text(960, 160, `sc.icon 全部 kind（${ICON_KINDS.length} 个）`, {size: 36, weight: 600});
  sc.fade(title, t0);
  ICON_KINDS.forEach((kind, i) => {
   const c = i % cols, r = Math.floor(i / cols);
   const cx = cellW * (c + .5), cy = top + cellH * (r + .5);
   const g = sc.icon(kind, cx, cy, .58);
   sc.pop(g, t0 + .3 + i * .09);
   const lbl = sc.text(cx, cy + cellH * .48, kind, {size: 20, color: GRAY});
   sc.fade(lbl, t0 + .3 + i * .09 + .15, .3, 6);
  });
 },

 // 角色道具 helper：xiaohei robot phone paper bubble cloud stamp check cross hourglass，5x2 网格。
 probe_chars(sc, s) {
  const t0 = sc.t0, cols = 5, cellW = 1920 / cols, top = 160, cellH = (860 - top) / 2;
  const title = sc.text(960, 130, '角色道具 helper', {size: 36, weight: 600});
  sc.fade(title, t0);
  const items = [
   ['xiaohei', (cx, cy) => sc.xiaohei(cx, cy, .8)],
   ['robot', (cx, cy) => sc.robot(cx, cy, .8)],
   ['phone', (cx, cy) => sc.phone(cx - 70, cy - 95, 140, 190)],
   ['paper', (cx, cy) => sc.paper(cx - 70, cy - 85, 140, 170)],
   ['bubble', (cx, cy) => sc.bubble(cx - 90, cy - 70, 180, 120, cx, cy + 90)],
   ['cloud', (cx, cy) => sc.cloud(cx - 90, cy - 55, 180, 110)],
   ['stamp', (cx, cy) => sc.stamp(cx, cy, 'OK', BLUE)],
   ['check', (cx, cy) => sc.check(cx, cy, 1.8, GREEN)],
   ['cross', (cx, cy) => sc.cross(cx, cy, 1.8, RED)],
   ['hourglass', (cx, cy) => sc.hourglass(cx, cy)],
  ];
  items.forEach(([name, draw], i) => {
   const c = i % cols, r = Math.floor(i / cols);
   const cx = cellW * (c + .5), cy = top + cellH * (r + .5);
   const node = draw(cx, cy);
   sc.draw(node, t0 + .3 + i * .35, .6);
   const lbl = sc.text(cx, cy + cellH * .42, name, {size: 22, color: GRAY});
   sc.fade(lbl, t0 + .3 + i * .35 + .3, .3, 6);
  });
 },

 // 纸条 note() + mark()/ringSpan()/strikeSpan() 三种标注各来一次。
 probe_notes(sc, s) {
  const t0 = sc.t0;
  const html = '这是探针纸条，用来检查 <span class="hl" id="pnMark">mark 高亮扫过</span>、'
   + '<span id="pnRing">ringSpan 红圈</span> 和 <span id="pnStrike">strikeSpan 划掉</span> 三种标注长什么样。';
  const n = sc.note(260, 240, 1400, html, t0 + .2, {size: 44, tag: '纸条示例', drawDur: .7});
  sc.mark(n.el.querySelector('#pnMark'), t0 + 1.6);
  sc.ringSpan(n.el.querySelector('#pnRing'), t0 + 2.6);
  sc.strikeSpan(n.el.querySelector('#pnStrike'), t0 + 3.6);
  const lbl = sc.text(960, 620, 'sc.note + sc.mark / sc.ringSpan / sc.strikeSpan', {size: 28, color: GRAY});
  sc.fade(lbl, t0 + 4.4);
 },

 // 结尾金句 sc.remember() 样式。
 probe_remember(sc, s) {
  const t0 = sc.t0;
  sc.remember('探针跑通，这句金句就是这个样子', '贯穿句示例：探针验证共用层渲染正常', t0 + .3, t0 + 1.8);
 },
});
