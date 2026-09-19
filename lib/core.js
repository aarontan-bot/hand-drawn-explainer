// 共享手绘程序层：Scene 基础方法 + 通用构建器（title/illus/single/end）；本集独有的画法写在 episode.js 里，不要改这份文件。
// sc.chip(...) 是从第 3–9 集 episode.js 顶层各自重复的 chip(sc,...) 收进来的胶囊标签方法。
const INK='#1E1C1A',RED='#D9483B',ORG='#E8963A',BLUE='#2F6FDB',GREEN='#3E9B5F',PURPLE='#7B5BC7',GRAY='#6F695F',PAPER='#FFFFFF';
const SVGNS='http://www.w3.org/2000/svg';
let SEED=11;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

class Scene{
 constructor(s){
  this.s=s;this.t0=s.start;this.t1=s.end;this.ev=s.events;
  this.el=document.createElement('section');this.el.className='scene';main.appendChild(this.el);
  this.svg=document.createElementNS(SVGNS,'svg');this.svg.setAttribute('class','stage');this.svg.setAttribute('viewBox','0 0 1920 1080');
  this.el.appendChild(this.svg);this.rc=rough.svg(this.svg);
 }
 at(k,d=0){const v=this.ev[k];if(v===undefined)throw Error(`scene ${this.s.no} missing event ${k}`);return v+d}
 opt(o={}){return Object.assign({seed:SEED++,roughness:1.1,bowing:.9,stroke:INK,strokeWidth:3.2,disableMultiStroke:false},o)}
 add(node,parent){(parent||this.svg).appendChild(node);return node}
 group(){return this.add(document.createElementNS(SVGNS,'g'))}
 // 线条逐笔展开；实心填充随后淡入
 draw(node,t,dur=.8){
  gsap.set(node,{opacity:0});tl.set(node,{opacity:1},t);
  node.querySelectorAll('path').forEach(p=>{
   const stroke=p.getAttribute('stroke');
   if(!stroke||stroke==='none'){tl.fromTo(p,{opacity:0},{opacity:1,duration:dur*.5},t+dur*.5);return}
   const len=p.getTotalLength();if(!len)return;
   p.style.strokeDasharray=len;p.style.strokeDashoffset=len;
   tl.to(p,{strokeDashoffset:0,duration:dur,ease:'power1.inOut'},t);
  });
  return node;
 }
 pop(node,t,dur=.4){tl.fromTo(node,{opacity:0,scale:.6,transformOrigin:'50% 50%'},{opacity:1,scale:1,duration:dur,ease:'back.out(2)'},t);return node}
 fade(node,t,dur=.45,y=14){tl.fromTo(node,{opacity:0,y},{opacity:1,y:0,duration:dur,ease:'power2.out'},t);return node}
 out(node,t,dur=.35){tl.to(node,{opacity:0,duration:dur},t);return node}
 // ---- 基础图形 ----
 line(x1,y1,x2,y2,o){return this.add(this.rc.line(x1,y1,x2,y2,this.opt(o)))}
 rect(x,y,w,h,o){return this.add(this.rc.rectangle(x,y,w,h,this.opt(o)))}
 circle(x,y,d,o){return this.add(this.rc.circle(x,y,d,this.opt(o)))}
 ellipse(x,y,w,h,o){return this.add(this.rc.ellipse(x,y,w,h,this.opt(o)))}
 path(d,o){return this.add(this.rc.path(d,this.opt(o)))}
 rrect(x,y,w,h,r,o){return this.path(`M${x+r} ${y}H${x+w-r}Q${x+w} ${y} ${x+w} ${y+r}V${y+h-r}Q${x+w} ${y+h} ${x+w-r} ${y+h}H${x+r}Q${x} ${y+h} ${x} ${y+h-r}V${y+r}Q${x} ${y} ${x+r} ${y}Z`,o)}
 arrow(d,x2,y2,ang,o={}){const g=this.group();g.appendChild(this.rc.path(d,this.opt(o)));const a=ang*Math.PI/180,l=26;
  g.appendChild(this.rc.line(x2,y2,x2-l*Math.cos(a-.5),y2-l*Math.sin(a-.5),this.opt(o)));g.appendChild(this.rc.line(x2,y2,x2-l*Math.cos(a+.5),y2-l*Math.sin(a+.5),this.opt(o)));return g}
 text(x,y,str,{size=40,weight=500,color=INK,anchor='middle'}={}){const t=document.createElementNS(SVGNS,'text');t.setAttribute('x',x);t.setAttribute('y',y);t.setAttribute('text-anchor',anchor);t.setAttribute('fill',color);t.style.font=`${weight} ${size}px 'PingFang SC',sans-serif`;t.textContent=str;return this.add(t)}
 html(x,y,w,inner,cls='h',style=''){const d=document.createElement('div');d.className=cls;d.style.cssText=`left:${x}px;top:${y}px;width:${w}px;${style}`;d.innerHTML=inner;this.el.appendChild(d);return d}
 mark(span,t,dur=.5){tl.to(span,{backgroundSize:'100% 42%',duration:dur,ease:'power2.out'},t)}

 // 纸条：自动估算高度；文字一字不差
 note(x,y,w,text,t,{size=44,tag,tagColor=GRAY,weight=500,pad=40,lh=1.6,drawDur=.6}={}){
  const per=Math.max(1,Math.floor((w-pad*2)/size)),plain=text.replace(/<[^>]+>/g,''),lines=Math.ceil(plain.length/per)+(text.match(/<br>/g)||[]).length;
  const h=Math.round(lines*size*lh+pad*1.6);
  this.draw(this.paper(x,y,w,h),t,drawDur);
  if(tag){const tg=this.text(x+pad*.6,y-14,tag,{size:30,color:tagColor,anchor:'start',weight:600});this.fade(tg,t+.2)}
  const d=this.html(x+pad,y+pad*.8,w-pad*2,text,'note',`font-size:${size}px;font-weight:${weight};line-height:${lh}`);this.fade(d,t+drawDur*.5);
  return {el:d,h,x,y,w};
 }
 hourglassPause(s,x=1760,y=440){if(!s.pause)return;const [pt,pd]=s.pause;const hg=this.hourglass(x,y);this.draw(hg,pt,.6);
  tl.fromTo(hg,{rotation:0,svgOrigin:`${x} ${y}`},{rotation:180,duration:.8,ease:'power2.inOut',repeat:Math.max(0,Math.floor(pd/2)-1),repeatDelay:1.2},pt+.6);
  const th=this.text(x,y+120,'想一想',{size:36,color:GRAY});this.fade(th,pt+.3);this.out(hg,pt+pd-.2);this.out(th,pt+pd-.2)}
 remember(one,thru,O,Th,dim=[]){if(dim.length)tl.to(dim,{opacity:.15,duration:.5},O-.3);
  const a=this.html(0,560,1920,`<span class="hl rm">${one}</span>`,'h',`text-align:center;font-size:${one.length>20?60:72}px;font-weight:600`);this.fade(a,O+.2);this.mark(a.querySelector('.rm'),O+1.4,.9);
  if(thru){const b=this.html(0,720,1920,thru,'h','text-align:center;font-size:40px;color:#5A5348');this.fade(b,Th)}}

 // 按页面上文字的实际位置画圈或删除线（抵消入场动画的位移）
 spanBox(span){const r=span.getBoundingClientRect(),m=main.getBoundingClientRect(),k=1920/m.width;let dy=0,el=span;while(el&&el!==main){dy+=+(gsap.getProperty(el,'y')||0);el=el.parentElement}return {x:(r.left-m.left)*k,y:(r.top-m.top)*k-dy,w:r.width*k,h:r.height*k}}
 ringSpan(span,t,color=RED,pad=16){const b=this.spanBox(span);return this.draw(this.ellipse(b.x+b.w/2,b.y+b.h/2,b.w+pad*2,b.h+pad*1.3,{stroke:color,strokeWidth:4}),t,.5)}
 strikeSpan(span,t,color=RED){const b=this.spanBox(span);return this.draw(this.line(b.x-8,b.y+b.h*.56,b.x+b.w+8,b.y+b.h*.5,{stroke:color,strokeWidth:6}),t,.45)}
 // 胶囊标签（圆角矩形 + 居中文字），原来每集 episode.js 顶层各抄一份的 chip(sc,...) 收进来变成 sc.chip(...)
 chip(x,y,w,label,t,{color=INK,fill='#fff',size=44,h=92}={}){
  this.draw(this.rrect(x-w/2,y-h/2,w,h,h/2,{stroke:color,strokeWidth:4,fill,fillStyle:'solid'}),t,.5);
  const tx=this.text(x,y+size*.36,label,{size,weight:600,color});this.fade(tx,t+.25);return tx;
 }
 // ---- 角色与道具 ----
 xiaohei(x,y,s=1){const g=this.group();g.setAttribute('transform',`translate(${x} ${y}) scale(${s})`);
  g.appendChild(this.rc.path('M-58 40 C-72 -10 -52 -70 0 -72 C52 -70 72 -10 58 40 C50 62 -50 62 -58 40Z',this.opt({fill:INK,fillStyle:'solid',strokeWidth:2.5})));
  g.appendChild(this.rc.line(-26,52,-30,96,this.opt({strokeWidth:4})));g.appendChild(this.rc.line(26,52,30,96,this.opt({strokeWidth:4})));
  g.appendChild(this.rc.line(-38,96,-24,96,this.opt({strokeWidth:5})));g.appendChild(this.rc.line(24,96,38,96,this.opt({strokeWidth:5})));
  for(const ex of [-16,16]){const e=document.createElementNS(SVGNS,'ellipse');e.setAttribute('cx',ex);e.setAttribute('cy',-18);e.setAttribute('rx',6);e.setAttribute('ry',8);e.setAttribute('fill','#fff');g.appendChild(e)}
  return g}
 phone(x,y,w,h){const g=this.group();g.appendChild(this.rc.path(`M${x+30} ${y}H${x+w-30}Q${x+w} ${y} ${x+w} ${y+30}V${y+h-30}Q${x+w} ${y+h} ${x+w-30} ${y+h}H${x+30}Q${x} ${y+h} ${x} ${y+h-30}V${y+30}Q${x} ${y} ${x+30} ${y}Z`,this.opt({strokeWidth:4})));
  g.appendChild(this.rc.line(x+w/2-30,y+18,x+w/2+30,y+18,this.opt({strokeWidth:5})));return g}
 robot(x,y,s=1){const g=this.group();g.setAttribute('transform',`translate(${x} ${y}) scale(${s})`);
  g.appendChild(this.rc.circle(0,0,110,this.opt({fill:'#fff',fillStyle:'solid'})));
  g.appendChild(this.rc.line(0,-55,0,-80,this.opt()));g.appendChild(this.rc.circle(0,-86,14,this.opt()));
  g.appendChild(this.rc.path('M-38 -18 Q-38 -30 -24 -30 H24 Q38 -30 38 -18 V10 Q38 22 24 22 H-24 Q-38 22 -38 10Z',this.opt({fill:INK,fillStyle:'solid',strokeWidth:2})));
  for(const ex of [-13,13]){const e=document.createElementNS(SVGNS,'ellipse');e.setAttribute('cx',ex);e.setAttribute('cy',-4);e.setAttribute('rx',6);e.setAttribute('ry',9);e.setAttribute('fill','#fff');g.appendChild(e)}
  return g}
 paper(x,y,w,h,o={}){const f=26;return this.path(`M${x} ${y}H${x+w-f}L${x+w} ${y+f}V${y+h}H${x}Z M${x+w-f} ${y}V${y+f}H${x+w}`,Object.assign({fill:'#fff',fillStyle:'solid'},o))}
 bubble(x,y,w,h,tx,ty,o={}){const r=34,bx=Math.min(Math.max(tx,x+r+30),x+w-r-30);
  return this.path(`M${x+r} ${y}H${x+w-r}Q${x+w} ${y} ${x+w} ${y+r}V${y+h-r}Q${x+w} ${y+h} ${x+w-r} ${y+h}H${bx+22}L${tx} ${ty}L${bx-8} ${y+h}H${x+r}Q${x} ${y+h} ${x} ${y+h-r}V${y+r}Q${x} ${y} ${x+r} ${y}Z`,Object.assign({fill:'#fff',fillStyle:'solid'},o))}
 cloud(x,y,w,h,o={}){const c=[];for(let i=0;i<9;i++){const a=i/9*Math.PI*2;c.push([x+w/2+Math.cos(a)*w/2,y+h/2+Math.sin(a)*h/2])}
  let d=`M${c[0][0]} ${c[0][1]}`;for(let i=0;i<9;i++){const p=c[i],q=c[(i+1)%9];const mx=(p[0]+q[0])/2,my=(p[1]+q[1])/2;const ox=(mx-(x+w/2))*.35,oy=(my-(y+h/2))*.35;d+=`Q${mx+ox} ${my+oy} ${q[0]} ${q[1]}`}
  return this.path(d+'Z',Object.assign({fill:'#fff',fillStyle:'solid'},o))}
 stamp(x,y,label,color){const g=this.group();g.setAttribute('transform',`translate(${x} ${y}) rotate(-6)`);
  g.appendChild(this.rc.rectangle(-110,-40,220,80,this.opt({stroke:color,strokeWidth:4})));
  const t=document.createElementNS(SVGNS,'text');t.setAttribute('text-anchor','middle');t.setAttribute('y',16);t.setAttribute('fill',color);t.style.font=`600 44px 'PingFang SC'`;t.textContent=label;g.appendChild(t);return g}
 check(x,y,s=1,color=GREEN){return this.path(`M${x-20*s} ${y}L${x-4*s} ${y+18*s}L${x+26*s} ${y-22*s}`,{stroke:color,strokeWidth:6})}
 cross(x,y,s=1,color=RED){const g=this.group();g.appendChild(this.rc.line(x-22*s,y-22*s,x+22*s,y+22*s,this.opt({stroke:color,strokeWidth:6})));g.appendChild(this.rc.line(x+22*s,y-22*s,x-22*s,y+22*s,this.opt({stroke:color,strokeWidth:6})));return g}
 hourglass(x,y){return this.path(`M${x-40} ${y-60}H${x+40} M${x-40} ${y+60}H${x+40} M${x-32} ${y-60}Q${x-32} ${y-10} ${x} ${y}Q${x+32} ${y-10} ${x+32} ${y-60} M${x-32} ${y+60}Q${x-32} ${y+10} ${x} ${y}Q${x+32} ${y+10} ${x+32} ${y+60}`,{strokeWidth:3.5})}
 icon(kind,x,y,s=1){const g=this.group();g.setAttribute('transform',`translate(${x} ${y}) scale(${s})`);const A=(n)=>g.appendChild(n);const o=(v)=>this.opt(v);
  if(kind==='question'){A(this.rc.circle(0,0,120,o()));const t=document.createElementNS(SVGNS,'text');t.setAttribute('text-anchor','middle');t.setAttribute('y',26);t.style.font=`600 76px 'PingFang SC'`;t.setAttribute('fill',BLUE);t.textContent='?';A(t)}
  if(kind==='command'){A(this.rc.path('M-50 -18 L10 -46 V46 L-50 18 Z',o()));A(this.rc.rectangle(-70,-18,20,36,o()));A(this.rc.line(26,-20,50,-34,o({stroke:ORG})));A(this.rc.line(28,0,56,0,o({stroke:ORG})));A(this.rc.line(26,20,50,34,o({stroke:ORG})))}
  if(kind==='page'){A(this.rc.path('M-44 -60 H24 L44 -40 V60 H-44 Z',o({fill:'#fff',fillStyle:'solid'})));for(let i=0;i<5;i++)A(this.rc.line(-28,-30+i*18,28,-30+i*18,o({strokeWidth:2.2})))}
  if(kind==='cards'){A(this.rc.rectangle(-50,-46,64,82,o()));A(this.rc.rectangle(-14,-26,64,82,o({fill:'#fff',fillStyle:'solid'})));A(this.rc.line(-2,-4,38,-4,o({stroke:BLUE,strokeWidth:2.5})));A(this.rc.line(-2,14,30,14,o({stroke:BLUE,strokeWidth:2.5})))}
  if(kind==='sketch'){A(this.rc.rectangle(-58,-50,116,100,o()));A(this.rc.line(-10,-50,-10,6,o()));A(this.rc.line(-58,6,20,6,o()));A(this.rc.rectangle(24,20,24,20,o({stroke:ORG})));A(this.rc.circle(-34,-24,18,o({stroke:ORG})))}
  if(kind==='form'){A(this.rc.rectangle(-56,-56,112,112,o()));for(let i=0;i<3;i++){A(this.rc.line(-44,-26+i*32,-14,-26+i*32,o({strokeWidth:2.5})));A(this.rc.rectangle(-4,-38+i*32,50,24,o({stroke:BLUE,strokeWidth:2.2})))}}
  if(kind==='house'){A(this.rc.path('M-40 0 L0 -36 L40 0 V40 H-40 Z',o()));A(this.rc.rectangle(-10,14,20,26,o()))}
  if(kind==='flag'){A(this.rc.line(-20,40,-20,-50,o({strokeWidth:4})));A(this.rc.path('M-20 -50 L34 -34 L-20 -16 Z',o({stroke:RED,fill:RED,fillStyle:'solid'})))}
  if(kind==='eye'){A(this.rc.path('M-60 0 Q0 -50 60 0 Q0 50 -60 0 Z',o()));A(this.rc.circle(0,0,34,o({fill:INK,fillStyle:'solid'})))}
  if(kind==='think'){A(this.cloudNode(-62,-44,124,80));A(this.rc.circle(-30,52,16,o()));A(this.rc.circle(-44,72,9,o()))}
  if(kind==='book'){A(this.rc.path('M0 -30 Q-30 -46 -60 -34 V34 Q-30 22 0 38 Q30 22 60 34 V-34 Q30 -46 0 -30 V38',o()))}
  if(kind==='lens'){A(this.rc.circle(-8,-8,70,o()));A(this.rc.line(18,18,50,50,o({strokeWidth:6})))}
  if(kind==='brush'){A(this.rc.line(-40,40,30,-30,o({strokeWidth:6})));A(this.rc.path('M30 -30 L48 -48 Q58 -40 44 -24 Z',o({stroke:ORG,fill:ORG,fillStyle:'solid'})))}
  if(kind==='fork'){A(this.rc.path('M0 50 V10 L-40 -40 M0 10 L40 -40',o({strokeWidth:4})))}
  if(kind==='ruler'){A(this.rc.rectangle(-60,-18,120,36,o()));for(let i=0;i<6;i++)A(this.rc.line(-48+i*19,-18,-48+i*19,-4-(i%2)*6,o({strokeWidth:2})))}
  if(kind==='plus'){A(this.rc.line(-16,0,16,0,o({stroke:GREEN,strokeWidth:5})));A(this.rc.line(0,-16,0,16,o({stroke:GREEN,strokeWidth:5})))}

  if(kind==='target'){A(this.rc.circle(0,0,110,o()));A(this.rc.circle(0,0,62,o({stroke:RED})));A(this.rc.circle(0,0,16,o({stroke:RED,fill:RED,fillStyle:'solid'})));A(this.rc.line(0,0,52,-52,o({strokeWidth:4})))}
  if(kind==='people'){A(this.rc.circle(-26,-24,40,o()));A(this.rc.path('M-56 40 Q-26 -6 4 40',o()));A(this.rc.circle(28,-14,32,o({stroke:BLUE})));A(this.rc.path('M4 44 Q28 8 52 44',o({stroke:BLUE})))}
  if(kind==='stop'){A(this.rc.polygon([[-22,-54],[22,-54],[54,-22],[54,22],[22,54],[-22,54],[-54,22],[-54,-22]],o({stroke:RED,strokeWidth:4})));A(this.rc.line(-28,0,28,0,o({stroke:RED,strokeWidth:8})))}
  if(kind==='list'){for(let i=0;i<3;i++){A(this.rc.circle(-40,-30+i*30,10,o({fill:INK,fillStyle:'solid'})));A(this.rc.line(-24,-30+i*30,44,-30+i*30,o()))}}
  if(kind==='table'){A(this.rc.rectangle(-50,-40,100,80,o()));A(this.rc.line(-50,-12,50,-12,o()));A(this.rc.line(-50,14,50,14,o()));A(this.rc.line(-10,-40,-10,40,o()))}
  if(kind==='paras'){for(let i=0;i<3;i++){A(this.rc.line(-44,-34+i*30,44,-34+i*30,o()));A(this.rc.line(-44,-22+i*30,20,-22+i*30,o({strokeWidth:2})))}}
  if(kind==='diary'){A(this.rc.rectangle(-40,-50,80,100,o({stroke:ORG})));A(this.rc.line(-26,-50,-26,50,o({stroke:ORG})));A(this.rc.line(-12,-20,28,-20,o({strokeWidth:2})))}
  if(kind==='scroll'){A(this.rc.path('M-40 -44 H40 V44 H-40 Z',o({stroke:PURPLE})));A(this.rc.path('M-48 -44 Q-40 -56 -32 -44 M32 44 Q40 56 48 44',o({stroke:PURPLE})));A(this.rc.path('M-20 -16 Q0 -26 20 -16 M-20 8 Q0 -2 20 8',o({strokeWidth:2})))}
  if(kind==='news'){A(this.rc.rectangle(-52,-44,104,88,o({stroke:BLUE})));A(this.rc.rectangle(-40,-32,36,30,o({stroke:BLUE})));for(let i=0;i<3;i++)A(this.rc.line(4,-28+i*14,40,-28+i*14,o({strokeWidth:2})));A(this.rc.line(-40,16,40,16,o({strokeWidth:2})));A(this.rc.line(-40,30,24,30,o({strokeWidth:2})))}
  if(kind==='medal'){A(this.rc.path('M-18 -56 L0 -20 L18 -56',o({stroke:RED})));A(this.rc.circle(0,10,64,o({stroke:ORG,fill:'#FBE3B5',fillStyle:'solid'})))}
  if(kind==='cake'){A(this.rc.path('M-56 10 H56 V50 H-56 Z',o()));A(this.rc.path('M-56 10 Q0 -30 56 10',o()));A(this.rc.line(-19,10,-19,50,o({stroke:RED})));A(this.rc.line(19,10,19,50,o({stroke:RED})))}
  if(kind==='clock'){A(this.rc.circle(0,0,110,o()));A(this.rc.line(0,0,0,-36,o({strokeWidth:4})));A(this.rc.line(0,0,26,12,o({strokeWidth:4})))}
  if(kind==='hand'){A(this.rc.path('M-30 40 V-10 Q-30 -22 -20 -22 Q-10 -22 -10 -10 V-40 Q-10 -52 0 -52 Q10 -52 10 -40 V-10 Q10 -22 20 -22 Q30 -22 30 -10 V40 Z',o()))}
  if(kind==='star'){A(this.rc.polygon([[0,-50],[14,-16],[50,-14],[22,8],[31,44],[0,24],[-31,44],[-22,8],[-50,-14],[-14,-16]],o({stroke:ORG})))}
  if(kind==='bulb'){A(this.rc.path('M-26 14 Q-46 -10 -30 -34 Q-12 -58 12 -52 Q42 -42 34 -12 Q30 4 22 14 Z',o()));A(this.rc.line(-20,26,20,26,o()));A(this.rc.line(-14,40,14,40,o()))}
  if(kind==='chat'){A(this.rc.path('M-54 -40 H54 V26 H-10 L-30 48 V26 H-54 Z',o()));A(this.rc.line(-34,-16,34,-16,o({strokeWidth:2})));A(this.rc.line(-34,4,14,4,o({strokeWidth:2})))}
  if(kind==='photo'){A(this.rc.rectangle(-54,-40,108,80,o()));A(this.rc.path('M-54 30 L-16 -6 L10 20 L28 2 L54 30',o({stroke:GREEN})));A(this.rc.circle(26,-18,16,o({stroke:ORG})))}
  if(kind==='gear'){A(this.rc.circle(0,0,70,o()));A(this.rc.circle(0,0,26,o()));for(let i=0;i<8;i++){const a=i/8*Math.PI*2;A(this.rc.line(Math.cos(a)*35,Math.sin(a)*35,Math.cos(a)*50,Math.sin(a)*50,o({strokeWidth:5})))}}
  if(kind==='loop'){A(this.rc.arc(0,0,110,110,-Math.PI*.9,Math.PI*.7,false,o({stroke:BLUE,strokeWidth:4})));A(this.rc.line(38,40,52,26,o({stroke:BLUE,strokeWidth:4})));A(this.rc.line(38,40,24,28,o({stroke:BLUE,strokeWidth:4})))}
  if(kind==='lock'){A(this.rc.rectangle(-40,-6,80,62,o()));A(this.rc.path('M-24 -6 V-28 Q-24 -52 0 -52 Q24 -52 24 -28 V-6',o()));A(this.rc.circle(0,22,14,o({fill:INK,fillStyle:'solid'})))}
  if(kind==='key'){A(this.rc.circle(-30,0,50,o({stroke:ORG})));A(this.rc.line(-5,0,56,0,o({stroke:ORG,strokeWidth:5})));A(this.rc.line(40,0,40,18,o({stroke:ORG,strokeWidth:5})));A(this.rc.line(54,0,54,14,o({stroke:ORG,strokeWidth:5})))}
  if(kind==='shelf'){A(this.rc.line(-60,40,60,40,o()));for(let i=0;i<5;i++)A(this.rc.rectangle(-54+i*22,-30+(i%2)*10,16,70-(i%2)*10,o({stroke:[RED,BLUE,GREEN,ORG,PURPLE][i]})))}
  return g}
 cloudNode(x,y,w,h){const n=this.cloud(x,y,w,h);n.remove();return n}
 // ---- 插画 ----
 art(no,single=false){const a=document.createElement('div');a.className='art';
  a.innerHTML=single?`<div class="half" style="background-image:url(assets/illus-${no}.png)"></div>`:`<div class="half l" style="background-image:url(assets/illus-${no}.png)"></div><div class="half r" style="background-image:url(assets/illus-${no}.png)"></div>`;
  this.el.insertBefore(a,this.svg);a.appendChild(this.svg);return a}
 finish(){tl.set(this.el,{visibility:'visible'},this.t0);tl.set(this.el,{visibility:'hidden'},this.t1);tl.fromTo(this.el,{opacity:0},{opacity:1,duration:.35},this.t0)}
}


const BUILD={
 title(sc){const t=sc.t0;
  const ep=sc.html(0,300,1920,`第 ${EP.no} 集`,'h','text-align:center;font-size:40px;letter-spacing:8px;color:'+BLUE);sc.fade(ep,t+.3);
  const h=sc.html(0,370,1920,EP.title,'h',`text-align:center;font-size:${EP.title.length>9?96:120}px;font-weight:600;letter-spacing:6px`);sc.fade(h,t+.6,.7,24);
  const w=Math.min(760,EP.title.length*(EP.title.length>9?96:120)*.55);
  sc.draw(sc.path(`M${960-w} 540 C ${960-w/2} 522, ${960+w/2} 552, ${960+w} 532`,{stroke:ORG,strokeWidth:7}),t+1.3,.8);
  const sub=sc.html(0,590,1920,EP.sub,'h','text-align:center;font-size:44px;color:#5A5348');sc.fade(sub,t+1.8);
  const bx=960+Math.min(820,EP.title.length*(EP.title.length>9?96:120)/2)+20;
  sc.draw(sc.bubble(bx,250,130,86,bx+10,360,{strokeWidth:3}),t+2.2,.7);
  const q=sc.text(bx+65,310,EP.mark||'?',{size:56,weight:600,color:BLUE});sc.pop(q,t+2.8);
 },

 illus(sc,s){const no=String(s.no).padStart(2,'0'),mk=D.marks[no]||{},art=sc.art(no);
  tl.fromTo(art,{scale:.87},{scale:.9,duration:sc.t1-sc.t0,ease:'none'},sc.t0);
  const sp=(mk.split||.5)*100;
  tl.fromTo(art.querySelector('.l'),{clipPath:'inset(0 100% 0 0)'},{clipPath:`inset(0 ${100-sp}% 0 0)`,duration:1.3,ease:'power2.out'},sc.t0+.1);
  tl.fromTo(art.querySelector('.r'),{clipPath:'inset(0 0 0 100%)'},{clipPath:`inset(0 0 0 ${sp}%)`,duration:1.3,ease:'power2.inOut'},s.events.right??sc.t0+2);
  if(mk.ring){const [x,y,r,c]=mk.ring;sc.draw(sc.ellipse(x,y,r*2.1,r*2,{stroke:c||BLUE,strokeWidth:5}),sc.at('mark'),.8)}
  if(mk.box){const [x,y,w,h,c]=mk.box;sc.draw(sc.rect(x,y,w,h,{stroke:c,strokeWidth:5}),sc.at('mark'),.9)}
  if(mk.q){const [x,y,c]=mk.q;const t=sc.text(x,y,'?',{size:70,weight:600,color:c||BLUE});t.setAttribute('stroke','#fff');t.setAttribute('stroke-width','8');t.setAttribute('paint-order','stroke');sc.pop(t,sc.at('mark'))}
  if(mk.arrow){const [d,x2,y2,ang,c]=mk.arrow;sc.draw(sc.arrow(d,x2,y2,ang,{stroke:c||BLUE,strokeWidth:6}),sc.at('mark'),.9)}
  if(s.events.t1){const a=mk.t1||[380,150],b=mk.t2||[1330,150];
   const p1=document.createElement('div');p1.className='pill';p1.style.cssText=`left:${a[0]}px;top:${a[1]}px`;p1.textContent='7:30';
   const p2=document.createElement('div');p2.className='pill late';p2.style.cssText=`left:${b[0]}px;top:${b[1]}px`;p2.textContent='9:00';
   art.append(p1,p2);sc.fade(p1,sc.at('t1'),.4,-10);sc.fade(p2,sc.at('t2'),.4,-10)}
 },

 single(sc,s){const no=String(s.no).padStart(2,'0'),art=sc.art(no,true);
  tl.fromTo(art,{scale:.87},{scale:.9,duration:sc.t1-sc.t0,ease:'none'},sc.t0);
  tl.fromTo(art.firstChild,{clipPath:'inset(0 100% 0 0)'},{clipPath:'inset(0 0% 0 0)',duration:1.8,ease:'power2.inOut'},sc.t0+.1);
 },

 end(sc){const t=sc.t0;
  // Logo 可选：D.logo 为 false 时（本集目录/系列目录都没放 assets/logo.png）不创建 img，避免 404
  if(D.logo){const i=document.createElement('img');i.src='assets/logo.png';i.style.cssText='position:absolute;left:640px;top:400px;width:640px;opacity:0';sc.el.appendChild(i);tl.to(i,{opacity:1,duration:.7},t+.2)}
  tl.to(main.querySelector('.brand'),{opacity:0,duration:.4},t);tl.to(main.querySelector('.series'),{opacity:0,duration:.4},t)},

};
