import type {Investigation, GraphNode, GraphEdge} from './types.js';
import {esc, date, link} from './ui.js';
type Point = {x:number; y:number; vx:number; vy:number};
const NS = 'http://www.w3.org/2000/svg';

export class ClaimGraph {
 host: HTMLElement;
 report: Investigation;
 svg!: SVGSVGElement;
 layer!: SVGGElement;
 points = new Map<string, Point>();
 nodes: GraphNode[] = [];
 edges: GraphEdge[] = [];
 zoom = 1; pan = {x:0,y:0};
 selected = ''; path = new Set<string>();
 mode = 'tree'; filter = 'all'; showClaim = false; inferred = true;
 cutoff = Infinity; frame = 0; generation = 0;
 onKey: (event: KeyboardEvent) => void;
 constructor(host:HTMLElement, report:Investigation) {
  this.host = host; this.report = report;
  this.onKey = e => {if(e.key === 'Escape') this.closePanel();};
  document.addEventListener('keydown',this.onKey);
  this.mount();
 }
 destroy() {this.generation++; cancelAnimationFrame(this.frame); document.removeEventListener('keydown', this.onKey);}
 closePanel() {this.host.querySelector('.node-panel')?.classList.add('hidden');}
 mount() {
  const dates = [...new Set(this.report.graph.nodes.map(n => n.publishedAt).filter(Boolean))].sort() as string[];
  this.host.innerHTML = `<div class="graph-toolbar"><div class="segmented"><button data-layout="tree" class="active">Spread tree</button><button data-layout="network">Network</button></div><label>Show <select id="graph-filter"><option value="all">All sources</option><option value="supports">Supports</option><option value="refutes">Refutes</option><option value="context">Context</option><option value="factcheck">Fact checks</option></select></label><label><input type="checkbox" id="inferred" checked> Possible links</label><label><input type="checkbox" id="claim-links"> Claim connections</label></div>
  <div class="graph-shell"><svg class="network" viewBox="0 0 1100 560" role="img" aria-label="Interactive source citation graph"><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#8e9695"/></marker></defs><g class="viewport"></g></svg><div class="graph-controls"><button data-action="plus" aria-label="Zoom in">+</button><button data-action="minus" aria-label="Zoom out">−</button><button data-action="fit">Fit</button><button data-action="reset">Reset</button></div><div class="graph-note"></div><aside class="node-panel hidden" aria-label="Selected source"></aside></div>
  <div class="graph-bottom"><div class="legend"><span class="supports">● Supports</span><span class="refutes">● Refutes</span><span class="context">● Context</span><span>◇ Fact check</span><span>◎ Earliest found</span><span>┄ Possible link</span></div><p class="small muted">Arrows point from the citing page to the page it links to. Tree placement shows citation ancestry, not proven transmission.</p><label class="time-control">Explore by publication date <input id="time" type="range" min="0" max="${dates.length}" value="${dates.length}" ${dates.length ? '' : 'disabled'}><output id="time-label">All dates</output></label>
  <details><summary>Trace a citation path</summary><div class="path-controls"><label>From <select id="path-from"></select></label><label>To <select id="path-to"></select></label><button id="trace-path">Trace path</button><button id="clear-path">Clear</button></div><p id="path-result" class="small" aria-live="polite">Find a directed path through observed citations. Possible links are excluded.</p></details></div>`;
  this.svg = this.host.querySelector('svg.network')!;
  this.layer = this.host.querySelector('.viewport')!;
  this.host.querySelectorAll<HTMLButtonElement>('[data-layout]').forEach(b => b.onclick = () => {this.mode=b.dataset.layout!; this.host.querySelectorAll('[data-layout]').forEach(x=>x.classList.toggle('active', x===b)); this.render();});
  this.host.querySelector<HTMLSelectElement>('#graph-filter')!.onchange = e => {this.filter=(e.target as HTMLSelectElement).value; this.render();};
  this.host.querySelector<HTMLInputElement>('#inferred')!.onchange = e => {this.inferred=(e.target as HTMLInputElement).checked; this.render();};
  this.host.querySelector<HTMLInputElement>('#claim-links')!.onchange = e => {this.showClaim=(e.target as HTMLInputElement).checked; this.render();};
  this.host.querySelector<HTMLInputElement>('#time')!.oninput = e => {const v=Number((e.target as HTMLInputElement).value); this.cutoff=v===dates.length?Infinity:v===0?-Infinity:new Date(dates[v-1]).getTime(); this.host.querySelector('#time-label')!.textContent=v===dates.length?'All dates':v===0?'Undated only':date(dates[v-1]); this.render();};
  this.host.querySelectorAll<HTMLButtonElement>('[data-action]').forEach(b => b.onclick=()=>{if(b.dataset.action==='plus')this.zoom=Math.min(3,this.zoom*1.2);else if(b.dataset.action==='minus')this.zoom=Math.max(.2,this.zoom/1.2);else if(b.dataset.action==='fit')this.fit();else {this.points.clear();this.render();} this.transform();});
  this.host.querySelector<HTMLButtonElement>('#trace-path')!.onclick=()=>this.trace();
  this.host.querySelector<HTMLButtonElement>('#clear-path')!.onclick=()=>{this.path.clear();this.draw();this.host.querySelector('#path-result')!.textContent='Path cleared.';};
  this.bindPointer(); this.render();
 }
 render() {
  this.generation++; cancelAnimationFrame(this.frame); this.path.clear();
  this.nodes=this.report.graph.nodes.filter(n=>(this.showClaim || n.id!=='claim') && (n.id==='claim' || this.filter==='all' || (this.filter==='factcheck'?n.type==='factcheck':n.stance===this.filter)) && (n.id==='claim' || !n.publishedAt || new Date(n.publishedAt).getTime()<=this.cutoff));
  const ids=new Set(this.nodes.map(n=>n.id));
  this.edges=this.report.graph.edges.filter(e=>ids.has(e.source)&&ids.has(e.target)&&(this.inferred||!e.isInferred));
  const rootParents=new Map(this.nodes.map(n=>[n.id,[] as string[]]));
  this.edges.filter(e=>!e.isInferred && e.target!=='claim').forEach(e=>rootParents.get(e.source)!.push(e.target));
  const depth=new Map<string,number>();
  const level=(id:string,visiting=new Set<string>()):number=>{if(depth.has(id))return depth.get(id)!;if(visiting.has(id))return 0;visiting.add(id);const d=Math.min(5,Math.max(-1,...rootParents.get(id)!.map(p=>level(p,new Set(visiting))))+1);depth.set(id,d);return d;};
  const rows=new Map<number,GraphNode[]>();
  this.nodes.forEach(n=>{const d=n.id==='claim'?0:level(n.id)+(this.showClaim?1:0);rows.set(d,[...(rows.get(d)||[]),n]);});
  const rowCount=[...rows.values()].reduce((sum,nodes)=>sum+Math.ceil(nodes.length/4),0);
  const height=Math.max(560,(rowCount+1)*145);
  this.svg.setAttribute('viewBox',`0 0 1100 ${height}`);
  if(this.mode==='tree') {
   let rowOffset=0;
   for(const [,nodes] of [...rows].sort((a,b)=>a[0]-b[0])){for(let start=0;start<nodes.length;start+=4){const chunk=nodes.slice(start,start+4);chunk.forEach((n,i)=>this.points.set(n.id,{x:(i+1)*1100/(chunk.length+1),y:90+rowOffset*145,vx:0,vy:0}));rowOffset++;}}
  } else {
   this.nodes.forEach((n,i)=>this.points.set(n.id,{x:n.id==='claim'?550:550+330*Math.cos(i*2*Math.PI/Math.max(1,this.nodes.length)),y:n.id==='claim'?height/2:height/2+220*Math.sin(i*2*Math.PI/Math.max(1,this.nodes.length)),vx:0,vy:0}));
  }
  this.zoom=1;this.pan={x:0,y:0};this.draw();this.transform();
  this.host.querySelector('.graph-note')!.textContent=this.nodes.length?`${this.nodes.length} nodes · ${this.edges.filter(e=>!e.isInferred).length} observed relationships · ${this.edges.filter(e=>e.isInferred).length} possible`:'No sources match these filters.';
  for(const select of this.host.querySelectorAll<HTMLSelectElement>('.path-controls select'))select.innerHTML=this.nodes.map(n=>`<option value="${esc(n.id)}">${esc(n.id+' · '+n.label)}</option>`).join('');
  if(!this.edges.length && this.nodes.length)this.host.querySelector('.graph-note')!.textContent += ' · No citation chain established';
  if(this.mode==='network')this.simulate(height,this.generation);
 }
 simulate(height:number,generation:number) {
  let tick=0;
  const step=()=>{
   if(generation!==this.generation || tick++>160)return;
   for(let i=0;i<this.nodes.length;i++)for(let j=i+1;j<this.nodes.length;j++){
    const a=this.points.get(this.nodes[i].id)!,b=this.points.get(this.nodes[j].id)!;const dx=a.x-b.x,dy=a.y-b.y,dist=Math.max(30,Math.hypot(dx,dy));const force=1800/(dist*dist);a.vx+=dx/dist*force;a.vy+=dy/dist*force;b.vx-=dx/dist*force;b.vy-=dy/dist*force;
   }
   this.edges.forEach(e=>{const a=this.points.get(e.source)!,b=this.points.get(e.target)!;const dx=b.x-a.x,dy=b.y-a.y,dist=Math.max(1,Math.hypot(dx,dy));const force=(dist-190)*.002;a.vx+=dx/dist*force;a.vy+=dy/dist*force;b.vx-=dx/dist*force;b.vy-=dy/dist*force;});
   for(const n of this.nodes){const p=this.points.get(n.id)!;p.vx=(p.vx+(550-p.x)*.0008)*.85;p.vy=(p.vy+(height/2-p.y)*.0008)*.85;p.x=Math.max(75,Math.min(1025,p.x+p.vx*6));p.y=Math.max(65,Math.min(height-70,p.y+p.vy*6));}
   this.draw();this.frame=requestAnimationFrame(step);
  };this.frame=requestAnimationFrame(step);
 }
 draw() {
  this.layer.innerHTML='';
  for(const edge of this.edges){const a=this.points.get(edge.source)!,b=this.points.get(edge.target)!;const dx=b.x-a.x,dy=b.y-a.y,d=Math.max(1,Math.hypot(dx,dy));const l=document.createElementNS(NS,'line');l.setAttribute('x1',String(a.x+dx/d*24));l.setAttribute('y1',String(a.y+dy/d*24));l.setAttribute('x2',String(b.x-dx/d*28));l.setAttribute('y2',String(b.y-dy/d*28));l.setAttribute('class','edge'+(edge.isInferred?' inferred':'')+(this.path.has(edge.source+'|'+edge.target)?' highlighted':''));l.setAttribute('marker-end','url(#arrow)');const title=document.createElementNS(NS,'title');title.textContent=edge.relationship+': '+edge.proof;l.append(title);this.layer.append(l);}
  for(const node of this.nodes){const p=this.points.get(node.id)!;const g=document.createElementNS(NS,'g');g.setAttribute('transform',`translate(${p.x},${p.y})`);g.setAttribute('class',`graph-node ${node.stance} ${node.type} ${node.id===this.selected?'selected':''}`);g.dataset.node=node.id;g.setAttribute('tabindex','0');g.setAttribute('role','button');g.setAttribute('aria-label',node.title);if(node.id===this.report.earliestSourceId){const outer=document.createElementNS(NS,'circle');outer.setAttribute('r','29');outer.setAttribute('class','earliest-ring');g.append(outer);}const shape=document.createElementNS(NS,node.type==='factcheck'?'rect':'circle');if(node.type==='factcheck'){shape.setAttribute('x','-17');shape.setAttribute('y','-17');shape.setAttribute('width','34');shape.setAttribute('height','34');shape.setAttribute('transform','rotate(45)');}else shape.setAttribute('r',node.type==='claim'?'25':'21');g.append(shape);const initial=document.createElementNS(NS,'text');initial.setAttribute('class','node-initial');initial.setAttribute('y','5');initial.textContent=node.id==='claim'?'C':node.id.toUpperCase();g.append(initial);const label=document.createElementNS(NS,'text');label.setAttribute('y','49');label.textContent=node.id==='claim'?'Investigated claim':node.label.slice(0,28);g.append(label);const stamp=document.createElementNS(NS,'text');stamp.setAttribute('y','68');stamp.setAttribute('class','node-date');stamp.textContent=node.id==='claim'?'':date(node.publishedAt);g.append(stamp);g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();this.select(node.id);}};this.layer.append(g);}
 }
 select(id:string){
  const n=this.report.graph.nodes.find(n=>n.id===id);if(!n)return;this.selected=id;
  const relations=this.report.graph.edges.filter(e=>e.source===id||e.target===id);
  const panel=this.host.querySelector<HTMLElement>('.node-panel')!;panel.classList.remove('hidden');
  panel.innerHTML=`<button class="close" aria-label="Close source details">×</button><div class="eyebrow">${esc(n.type)} · ${esc(n.id)}</div><h3>${esc(n.title)}</h3><p>${esc(n.publisher)}</p><p class="small">${date(n.publishedAt)} · <span class="${n.stance}">${esc(n.stance)}</span></p><p class="small">Stance confidence: ${n.confidence===null?'Unrated':Math.round(n.confidence*100)+'% (model estimate)'}</p>${id===this.report.earliestSourceId?'<p class="badge">Earliest source found in this investigation</p>':''}<blockquote>${esc(n.excerpt || 'The factual claim under investigation.')}</blockquote>${n.id==='claim'?'':link(n.url)}<h4>Relationships</h4>${relations.length?relations.map(e=>`<div class="relation"><strong>${esc(e.source)} → ${esc(e.target)}</strong><p>${esc(e.relationship.replaceAll('_',' '))}${e.isInferred?' · Possible relationship':''}</p><small>${esc(e.proof)}</small></div>`).join(''):'<p>No relationship has been established.</p>'}`;
  panel.querySelector<HTMLButtonElement>('.close')!.onclick=()=>this.closePanel();
 }
 transform(){this.layer.setAttribute('transform',`translate(${this.pan.x},${this.pan.y}) scale(${this.zoom})`);}
 fit(){if(!this.nodes.length)return;const points=this.nodes.map(n=>this.points.get(n.id)!);const minX=Math.min(...points.map(p=>p.x))-110,maxX=Math.max(...points.map(p=>p.x))+110,minY=Math.min(...points.map(p=>p.y))-60,maxY=Math.max(...points.map(p=>p.y))+90;const h=this.svg.viewBox.baseVal.height;this.zoom=Math.min(1100/(maxX-minX),h/(maxY-minY),1.6);this.pan={x:(1100-(maxX+minX)*this.zoom)/2,y:(h-(maxY+minY)*this.zoom)/2};}
 bindPointer(){
  let drag:{id:string|null;x:number;y:number;startX:number;startY:number;moved:boolean}|null=null;
  const point=(e:PointerEvent|WheelEvent)=>{const p=this.svg.createSVGPoint();p.x=e.clientX;p.y=e.clientY;return p.matrixTransform(this.svg.getScreenCTM()!.inverse());};
  this.svg.onpointerdown=e=>{const p=point(e);const node=(e.target as Element).closest<SVGGElement>('[data-node]');cancelAnimationFrame(this.frame);drag={id:node?.dataset.node||null,x:p.x,y:p.y,startX:e.clientX,startY:e.clientY,moved:false};this.svg.setPointerCapture(e.pointerId);};
  this.svg.onpointermove=e=>{if(!drag)return;const p=point(e);if(Math.abs(e.clientX-drag.startX)+Math.abs(e.clientY-drag.startY)>5)drag.moved=true;if(drag.id){const n=this.points.get(drag.id)!;n.x+=(p.x-drag.x)/this.zoom;n.y+=(p.y-drag.y)/this.zoom;this.draw();}else{this.pan.x+=p.x-drag.x;this.pan.y+=p.y-drag.y;this.transform();}drag.x=p.x;drag.y=p.y;};
  this.svg.onpointerup=()=>{if(drag?.id&&!drag.moved)this.select(drag.id);drag=null;};
  this.svg.onpointercancel=()=>{drag=null;};
  this.svg.onwheel=e=>{e.preventDefault();const p=point(e),old=this.zoom;this.zoom=Math.max(.2,Math.min(3,old*(e.deltaY>0?.9:1.1)));this.pan.x=p.x-(p.x-this.pan.x)*this.zoom/old;this.pan.y=p.y-(p.y-this.pan.y)*this.zoom/old;this.transform();};
 }
 trace(){
  const from=this.host.querySelector<HTMLSelectElement>('#path-from')!.value,to=this.host.querySelector<HTMLSelectElement>('#path-to')!.value;
  const adjacency=new Map(this.nodes.map(n=>[n.id,[] as string[]]));this.edges.filter(e=>!e.isInferred).forEach(e=>adjacency.get(e.source)!.push(e.target));
  const parent=new Map<string,string|null>([[from,null]]),queue=[from];
  for(let i=0;i<queue.length;i++)for(const next of adjacency.get(queue[i])||[])if(!parent.has(next)){parent.set(next,queue[i]);queue.push(next);}
  this.path.clear();const result=this.host.querySelector('#path-result')!;
  if(!parent.has(to)){result.textContent='No observed directed citation path exists between these sources in the current view.';this.draw();return;}
  const chain:string[]=[];let current:string|null=to;while(current!==null){chain.push(current);current=parent.get(current)??null;}chain.reverse();for(let i=1;i<chain.length;i++)this.path.add(chain[i-1]+'|'+chain[i]);result.textContent='Observed citation path: '+chain.join(' → ')+'. This does not establish who first spread the claim.';this.draw();
 }
}
