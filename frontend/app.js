'use strict';
const $ = (id) => document.getElementById(id);
const api = (p, o) => fetch(p, o).then(r => r.json());

/* ── Iconos (SVG inline, estilo Lucide, sin CDN) ───────────────────────── */
const ICONS = {
  scan:'<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 12h10"/>',
  cpu:'<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M15 2v2M15 20v2M2 15h2M2 9h2M20 15h2M20 9h2M9 2v2M9 20v2"/>',
  clock:'<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
  film:'<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 3v18M3 7.5h4M3 12h18M3 16.5h4M17 3v18M17 7.5h4M17 16.5h4"/>',
  play:'<polygon points="6 3 20 12 6 21 6 3"/>',
  stop:'<rect width="14" height="14" x="5" y="5" rx="2"/>',
  rows:'<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18M3 15h18"/>',
  undo:'<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
  trash:'<path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M10 11v6M14 11v6"/>',
  users:'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  route:'<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
  layers:'<path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 12.5-9.17 4.16a2 2 0 0 1-1.66 0L2 12.5"/><path d="m22 17.5-9.17 4.16a2 2 0 0 1-1.66 0L2 17.5"/>',
  download:'<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
  alert:'<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4M12 17h.01"/>',
  activity:'<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
  eye:'<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
  timer:'<line x1="10" x2="14" y1="2" y2="2"/><line x1="12" x2="12" y1="14" y2="9"/><circle cx="12" cy="14" r="8"/>',
  package:'<path d="M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73Z"/><path d="M3.3 7 12 12l8.7-5"/><path d="M12 22V12"/>',
  login:'<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" x2="3" y1="12" y2="12"/>',
  'user-check':'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><polyline points="16 11 18 13 22 9"/>',
  'mouse-pointer':'<path d="M12.586 12.586 19 19"/><path d="M3.688 3.037a.497.497 0 0 0-.651.651l6.5 15.999a.501.501 0 0 0 .947-.062l1.569-6.083a2 2 0 0 1 1.448-1.479l6.124-1.579a.5.5 0 0 0 .063-.947z"/>',
  'map-pin':'<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
  x:'<path d="M18 6 6 18M6 6l12 12"/>',
};
function svg(n){ return `<svg viewBox="0 0 24 24">${ICONS[n]||''}</svg>`; }
function hydrateIcons(root){ (root||document).querySelectorAll('i[data-ico]').forEach(el=>{ if(!el.firstChild) el.innerHTML=svg(el.dataset.ico); }); }

const PALETTE = ['#F26A21','#2D6CDF','#129A6B','#E19100','#7C5CE0','#E5484D','#0EA5A5'];
const SEV = { critical:'#E5484D', warning:'#E19100', info:'#2D6CDF', ok:'#129A6B' };
const MODCOL = { Conteo:'#2D6CDF', Permanencia:'#129A6B', Anaqueles:'#E19100' };

/* Config por caso de uso */
const UC = {
  conteo:      { tool:'line',  det:'yolo', drawLbl:'Dibujar línea',   cfg:'Dibuja la línea',    ph:'línea de conteo',
                 title:'Conteo de personas', need:()=>!!st.line, msg:'Primero dibuja la línea de conteo' },
  permanencia: { tool:'zone',  det:'yolo', drawLbl:'Dibujar zona',    cfg:'Dibuja las zonas',   ph:'zona de permanencia',
                 title:'Permanencia por zona', need:()=>st.zones.some(z=>z.type!=='anaquel'), msg:'Primero dibuja al menos una zona' },
  anaqueles:   { tool:'shelf', det:'yoloworld', drawLbl:'Marcar anaquel', cfg:'Marca los anaqueles', ph:'zona de anaquel',
                 title:'Nivel de anaquel', need:()=>st.zones.some(z=>z.type==='anaquel'), msg:'Primero marca al menos un anaquel' },
};

const st = { usecase:'conteo', video:null, tool:null, line:null, zones:[], draft:[], streaming:false, statusTimer:null };

/* ── init ──────────────────────────────────────────────────────────────── */
(async function init(){
  hydrateIcons();
  const d = await api('/api/videos');
  $('devicePill').textContent = `${d.variant} · ${d.device}`;
  $('kCap').textContent = 'Dentro · aforo ' + d.store_capacity;
  const sel = $('videoSelect');
  sel.innerHTML = d.videos.length
    ? d.videos.map(v=>`<option>${v}</option>`).join('')
    : '<option value="">(coloca .mp4 en videos/)</option>';
  // detectores
  const ds=$('detectorSelect');
  ds.innerHTML=(d.detectors||[]).map(x=>`<option value="${x.kind}">${x.label}</option>`).join('');
  ds.value=d.default_detector||'yolo';
  tickClock(); setInterval(tickClock, 1000);
  applyUsecase();
  if (d.videos.length){ sel.value=d.videos[0]; await loadVideo(d.videos[0]); }
})();
function tickClock(){ $('clock').textContent = new Date().toLocaleTimeString('es-PE',{hour:'2-digit',minute:'2-digit',second:'2-digit'}); }

/* ── caso de uso ───────────────────────────────────────────────────────── */
document.querySelectorAll('.uc').forEach(b=>b.onclick=()=>{
  if(st.streaming){ toast('Detén el proceso para cambiar de módulo'); return; }
  document.querySelectorAll('.uc').forEach(x=>x.classList.remove('active'));
  b.classList.add('active');
  st.usecase=b.dataset.uc; st.tool=null; st.draft=[];
  applyUsecase();
});
function applyUsecase(){
  const u=UC[st.usecase];
  $('drawLbl').textContent=u.drawLbl;
  $('stepCfgTxt').textContent=u.cfg;
  $('phCfg').textContent=u.ph;
  $('ucTitle').textContent=u.title;
  $('drawBtn').dataset.active='0';
  // auto-selecciona el detector correcto para este caso de uso
  const ds=$('detectorSelect'); if(ds && u.det) ds.value=u.det;
  document.querySelectorAll('.mod-panel').forEach(p=>p.style.display=(p.dataset.mod===st.usecase)?'block':'none');
  renderChips(); redraw(); updateSteps();
}

/* ── carga de video ────────────────────────────────────────────────────── */
async function loadVideo(name){
  st.video=name; st.streaming=false; stopStream();
  $('placeholder').style.display='none';
  const img=$('frameImg'); img.style.display='block';
  img.onload=()=>{ sizeEditor(); redraw(); };
  img.src=`/api/video/${encodeURIComponent(name)}/frame?t=${Date.now()}`;
  const cfg=await api(`/api/video/${encodeURIComponent(name)}/zones`);
  st.line=cfg.line||null;
  st.zones=(cfg.zones||[]).map((z,i)=>({...z,color:z.color||PALETTE[i%PALETTE.length]}));
  st.draft=[]; renderChips(); redraw(); updateSteps();
}
$('videoSelect').addEventListener('change', e=>{ if(e.target.value) loadVideo(e.target.value); });

/* ── geometría editor ──────────────────────────────────────────────────── */
function imgRect(){
  const img=$('frameImg'), vp=$('viewport');
  const cw=vp.clientWidth, ch=vp.clientHeight;
  const nw=img.naturalWidth||cw, nh=img.naturalHeight||ch;
  const s=Math.min(cw/nw, ch/nh), w=nw*s, h=nh*s;
  return { x:(cw-w)/2, y:(ch-h)/2, w, h };
}
function sizeEditor(){ const vp=$('viewport'), cv=$('editor'); cv.width=vp.clientWidth; cv.height=vp.clientHeight; }
window.addEventListener('resize', ()=>{ sizeEditor(); redraw(); });
function toNorm(cx,cy){ const r=imgRect(); return [(cx-r.x)/r.w,(cy-r.y)/r.h]; }
function toPx(nx,ny){ const r=imgRect(); return [r.x+nx*r.w, r.y+ny*r.h]; }

/* elementos visibles según caso de uso */
function visibleZones(){ return st.zones.filter(z=> st.usecase==='anaqueles' ? z.type==='anaquel' : (st.usecase==='permanencia' && z.type!=='anaquel')); }

/* ── herramienta de dibujo ─────────────────────────────────────────────── */
$('drawBtn').onclick=()=>toggleTool();
function toggleTool(){
  const t=UC[st.usecase].tool;
  st.tool=(st.tool===t)?null:t; st.draft=[];
  $('drawBtn').dataset.active=st.tool?'1':'0';
  const h=$('hint');
  if(st.tool==='line'){ h.style.display='block'; h.textContent='Haz clic en 2 puntos para la línea de conteo'; }
  else if(st.tool){ h.style.display='block'; h.textContent='Clic para marcar puntos · doble clic para cerrar'; }
  else h.style.display='none';
  redraw();
}
$('editor').addEventListener('click', e=>{
  if(!st.tool||st.streaming) return;
  const r=$('editor').getBoundingClientRect();
  const [nx,ny]=toNorm(e.clientX-r.left, e.clientY-r.top);
  if(nx<0||nx>1||ny<0||ny>1) return;
  if(st.tool==='line'){ st.draft.push([nx,ny]); if(st.draft.length===2){ st.line={a:st.draft[0],b:st.draft[1]}; st.draft=[]; toggleTool(); afterEdit(); } }
  else st.draft.push([nx,ny]);
  redraw();
});
$('editor').addEventListener('dblclick', e=>{
  if(!st.tool||st.tool==='line'||st.streaming) return;
  if(st.draft.length<3){ toast('Marca al menos 3 puntos'); return; }
  const type=st.tool==='shelf'?'anaquel':'permanencia';
  const name=prompt(type==='anaquel'?'Nombre del anaquel (ej. "Anaquel A"):':'Nombre de la zona (ej. "Caja 1"):');
  if(!name) return;
  const color=PALETTE[st.zones.length%PALETTE.length];
  st.zones.push({ id:'z'+(st.zones.length+1)+'_'+Date.now().toString(36), name, type, color, points:st.draft.slice() });
  st.draft=[]; toggleTool(); afterEdit();
});
$('undoBtn').onclick=()=>{
  if(st.draft.length){ st.draft.pop(); redraw(); return; }
  if(st.usecase==='conteo'){ st.line=null; }
  else { const vis=visibleZones(); if(vis.length){ const last=vis[vis.length-1]; st.zones=st.zones.filter(z=>z!==last); } }
  afterEdit();
};
$('clearBtn').onclick=()=>{
  if(st.usecase==='conteo') st.line=null;
  else if(st.usecase==='permanencia') st.zones=st.zones.filter(z=>z.type==='anaquel');
  else st.zones=st.zones.filter(z=>z.type!=='anaquel');
  st.draft=[]; afterEdit();
};
function afterEdit(){ renderChips(); redraw(); updateSteps(); }

/* ── dibujo overlay ────────────────────────────────────────────────────── */
function redraw(){
  const cv=$('editor'); if(!cv.width) sizeEditor();
  const ctx=cv.getContext('2d'); ctx.clearRect(0,0,cv.width,cv.height);
  if(st.streaming) return;
  visibleZones().forEach(z=>drawPoly(ctx,z.points,z.color,z.name));
  if(st.usecase==='conteo' && st.line) drawLine(ctx,st.line.a,st.line.b,'#E5484D','CONTEO');
  if(st.draft.length){
    if(st.tool==='line'&&st.draft.length===1){ const [x,y]=toPx(...st.draft[0]); dot(ctx,x,y,'#F26A21'); }
    else drawPoly(ctx,st.draft,'#F26A21','',true);
  }
}
function drawPoly(ctx,pts,color,label,dashed){
  if(!pts.length) return; ctx.save();
  ctx.beginPath(); pts.forEach((p,i)=>{ const [x,y]=toPx(...p); i?ctx.lineTo(x,y):ctx.moveTo(x,y); });
  if(!dashed) ctx.closePath();
  ctx.fillStyle=hexA(color,.16); ctx.fill();
  ctx.lineWidth=2.5; ctx.strokeStyle=color; if(dashed)ctx.setLineDash([7,5]); ctx.stroke();
  pts.forEach(p=>{ const [x,y]=toPx(...p); dot(ctx,x,y,color); });
  if(label){ const [x,y]=toPx(...pts[0]); ctx.setLineDash([]); ctx.fillStyle=color; ctx.font='700 13px Inter,sans-serif'; ctx.fillText(label,x+5,y-7); }
  ctx.restore();
}
function drawLine(ctx,a,b,color,label){
  const [x1,y1]=toPx(...a),[x2,y2]=toPx(...b); ctx.save();
  ctx.strokeStyle=color; ctx.lineWidth=3.5; ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); ctx.stroke();
  dot(ctx,x1,y1,color); dot(ctx,x2,y2,color);
  ctx.fillStyle=color; ctx.font='700 12px Inter,sans-serif'; ctx.fillText(label,x1,y1-9); ctx.restore();
}
function dot(ctx,x,y,c){ ctx.beginPath(); ctx.arc(x,y,4.5,0,7); ctx.fillStyle=c; ctx.fill(); ctx.lineWidth=2; ctx.strokeStyle='#fff'; ctx.stroke(); }
function hexA(h,a){ h=h.replace('#',''); return `rgba(${parseInt(h.slice(0,2),16)},${parseInt(h.slice(2,4),16)},${parseInt(h.slice(4,6),16)},${a})`; }

function renderChips(){
  const wrap=$('zoneChips'); let html='';
  if(st.usecase==='conteo'){ if(st.line) html+=chip('Línea de conteo','#E5484D','scan','line',0); }
  else visibleZones().forEach((z)=>{ const idx=st.zones.indexOf(z); html+=chip(z.name,z.color,z.type==='anaquel'?'rows':'timer','zone',idx); });
  wrap.innerHTML=html; hydrateIcons(wrap);
  $('noZones').style.display=html?'none':'inline';
  wrap.querySelectorAll('.x').forEach(el=>el.onclick=()=>{ const{kind,idx}=el.dataset; if(kind==='line')st.line=null; else st.zones.splice(+idx,1); afterEdit(); });
}
function chip(text,color,icon,kind,idx){
  return `<span class="chip" style="background:${hexA(color,.1)};color:${color};border-color:${hexA(color,.35)}"><i data-ico="${icon}"></i>${text}<span class="x" data-kind="${kind}" data-idx="${idx}"><i data-ico="x"></i></span></span>`;
}

/* ── pasos ─────────────────────────────────────────────────────────────── */
function updateSteps(){
  const hasVideo=!!st.video, hasCfg=UC[st.usecase].need();
  setStep(1, hasVideo?'done':'active');
  setStep(2, !hasVideo?'':(hasCfg?'done':'active'));
  setStep(3, st.streaming?'active':(hasVideo&&hasCfg?'active':''));
}
function setStep(n,state){ const el=document.querySelector(`.step[data-step="${n}"]`); el.className='step'+(state?' '+state:''); }

/* ── start / stop ──────────────────────────────────────────────────────── */
$('startBtn').onclick=start; $('stopBtn').onclick=stop;
async function start(){
  if(!st.video){ toast('Elige un video'); return; }
  if(!UC[st.usecase].need()){ toast(UC[st.usecase].msg); if(!st.tool) toggleTool(); return; }
  await saveZones();
  const zoneOnly = st.usecase==='permanencia';
  const r=await api('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({video:st.video,conf:0.4,detector:$('detectorSelect').value,zone_only:zoneOnly})});
  if(r.error){ toast(r.error); return; }
  st.streaming=true; redraw();
  $('frameImg').style.display='none';
  const s=$('stream'); s.style.display='block'; s.src='/stream?t='+Date.now();
  $('startBtn').disabled=true; $('stopBtn').disabled=false;
  $('liveDot').className='dot on'; $('liveTxt').textContent='Procesando';
  $('vpBadgeTxt').textContent='Tracking en vivo';
  $('procTxt').textContent='Cargando modelo…';
  $('procOverlay').style.display='flex';
  updateSteps();
  if(st.statusTimer) clearInterval(st.statusTimer);
  st.statusTimer=setInterval(poll,500);
}
async function stop(){ await fetch('/api/stop',{method:'POST'}); finishUI(); }
function stopStream(){ const s=$('stream'); s.style.display='none'; s.src=''; }
function finishUI(){
  st.streaming=false;
  $('procOverlay').style.display='none';
  $('startBtn').disabled=false; $('stopBtn').disabled=true;
  $('liveDot').className='dot'; $('liveTxt').textContent='Listo';
  $('vpBadgeTxt').textContent='Resultado';
  if(st.statusTimer){ clearInterval(st.statusTimer); st.statusTimer=null; }
  // fija el video actual (evita cualquier salto de video al terminar)
  if(st.video) $('videoSelect').value=st.video;
  updateSteps();
}
function saveZones(){ return fetch(`/api/video/${encodeURIComponent(st.video)}/zones`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({line:st.line,zones:st.zones})}); }

/* ── poll / render ─────────────────────────────────────────────────────── */
async function poll(){
  const s=await api('/api/status');
  // overlay de carga: se oculta cuando llega el primer frame anotado
  if(st.streaming){
    if(s.has_frame){ $('procOverlay').style.display='none'; }
    else { $('procOverlay').style.display='flex'; $('procTxt').textContent=s.model_ready?'Procesando…':'Cargando modelo…'; }
  }
  $('progressBar').style.width=(100*(s.progress||0))+'%';
  $('kUnique').textContent=s.unique_people??0;
  $('kIn').textContent=s.entered_total??s.total_in??0;
  $('kInside').textContent=s.dentro_now??s.inside??0;
  $('kDwell').textContent=s.avg_dwell??'0s';
  $('ioIn').textContent=s.total_in??0; $('ioOut').textContent=s.total_out??0; $('ioPeak').textContent=s.peak_inside??0;
  $('liveTxt').textContent=`${s.video_time||''} / ${s.duration||''}`;
  if(s.timeline) drawFlow(s.timeline, s.store_capacity);
  renderPeople(s.active_people||[], s.active_count||0);
  renderDwell(s.zones||[]); renderShelves(s.shelves||[]); renderAlerts(s.alerts||[]);
  if(s.finished){ finishUI(); toast('Procesamiento terminado · CSV listo'); }
}
function renderPeople(list,count){
  // en permanencia, solo mostrar a quienes están DENTRO de una zona
  if(st.usecase==='permanencia'){ list=list.filter(p=>p.zone); count=list.length; }
  $('activeCount').textContent=count;
  const el=$('activePeople');
  if(!list.length){ el.innerHTML='<div class="ps-empty">Sin personas en zona todavía.</div>'; return; }
  el.innerHTML=list.map(p=>{ const c=PALETTE[p.id%PALETTE.length];
    const badge = p.state==='entrante' ? '<span class="pbadge in">entrante</span>'
                : p.state==='visitante' ? '<span class="pbadge vis">visitante</span>' : '';
    return `<div class="person" style="border-left-color:${c}"><div class="pid"><i data-ico="user-check" style="color:${c}"></i>ID ${p.id}${badge}</div><div class="prow"><i data-ico="timer"></i>${p.dwell}</div><div class="prow"><i data-ico="map-pin"></i><span class="pzone">${p.zone||'en tránsito'}</span></div></div>`; }).join('');
  hydrateIcons(el);
}
function renderDwell(zones){
  const el=$('dwellTable');
  if(!zones.length){ el.innerHTML='<div class="zb-empty" style="padding:10px">Dibuja zonas de permanencia para medir el tiempo por zona.</div>'; return; }
  let h='<div class="row head"><span>Zona</span><span>Prom.</span><span>Máx.</span><span>Ahora</span></div>';
  zones.forEach(z=>{ h+=`<div class="row"><span class="zn"><span class="dot-s" style="background:${z.color}"></span>${z.name}</span><span class="zc">${z.avg}</span><span class="zc">${z.max}</span><span class="zp">${z.people_now}</span></div>`; });
  el.innerHTML=h;
}
function renderShelves(sh){
  const el=$('shelfBars');
  if(!sh.length){ el.innerHTML='<div class="zb-empty" style="padding:10px">Marca zonas tipo <b>anaquel</b> para estimar el nivel de llenado.</div>'; return; }
  el.innerHTML=sh.map(s=>{ const c=s.status==='critical'?'#E5484D':s.status==='warning'?'#E19100':'#129A6B';
    const right = s.mode==='objetos'
      ? `<span style="color:${c};font-weight:700">${s.count}/${s.expected}${s.missing?` · faltan ${s.missing}`:''}</span>`
      : `<span style="color:${c};font-weight:700">${Math.round(s.fill)}%</span>`;
    return `<div class="shelf"><div class="shelf-hd"><span class="shelf-nm"><span class="dot-s" style="background:${c}"></span>${s.name}</span>${right}</div><div class="shelf-track"><div class="shelf-fill" style="width:${s.fill}%;background:${c}"></div></div></div>`; }).join('');
}
function renderAlerts(al){
  $('alertCount').textContent=al.length;
  $('noAlerts').style.display=al.length?'none':'block';
  $('alertRows').innerHTML=[...al].reverse().map(a=>`<tr><td style="font-variant-numeric:tabular-nums">${a.video_time}</td><td><span class="mtag" style="background:${hexA(MODCOL[a.modulo]||'#2D6CDF',.1)};color:${MODCOL[a.modulo]||'#2D6CDF'}">${a.modulo}</span></td><td><span class="sev"><span class="d" style="background:${SEV[a.severity]||'#2D6CDF'}"></span>${a.tipo}</span></td><td class="hide-sm">${a.detalle}</td></tr>`).join('');
}

/* ── flow chart ────────────────────────────────────────────────────────── */
function drawFlow(tl, cap){
  const cv=$('flowChart'); const dpr=window.devicePixelRatio||1;
  const w=cv.clientWidth, h=cv.clientHeight; cv.width=w*dpr; cv.height=h*dpr;
  const ctx=cv.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,w,h);
  if(!tl.length) return;
  const pad={l:28,r:10,t:12,b:20}, gw=w-pad.l-pad.r, gh=h-pad.t-pad.b;
  const maxT=Math.max(1,tl[tl.length-1].t);
  const maxV=Math.max(cap||1,...tl.map(p=>Math.max(p.inside,p.ins,p.outs)),1);
  const X=t=>pad.l+(t/maxT)*gw, Y=v=>pad.t+gh-(v/maxV)*gh;
  ctx.strokeStyle='#EEF1F5'; ctx.fillStyle='#8791A3'; ctx.font='10px Inter'; ctx.lineWidth=1;
  for(let i=0;i<=4;i++){ const v=maxV*i/4, y=Y(v); ctx.beginPath(); ctx.moveTo(pad.l,y); ctx.lineTo(w-pad.r,y); ctx.stroke(); ctx.fillText(Math.round(v),5,y+3); }
  if(cap){ ctx.strokeStyle='rgba(229,72,77,.5)'; ctx.setLineDash([4,3]); ctx.beginPath(); ctx.moveTo(pad.l,Y(cap)); ctx.lineTo(w-pad.r,Y(cap)); ctx.stroke(); ctx.setLineDash([]); }
  ctx.beginPath(); ctx.moveTo(X(tl[0].t),Y(0)); tl.forEach(p=>ctx.lineTo(X(p.t),Y(p.inside))); ctx.lineTo(X(tl[tl.length-1].t),Y(0)); ctx.closePath();
  const g=ctx.createLinearGradient(0,pad.t,0,pad.t+gh); g.addColorStop(0,'rgba(111,168,12,.22)'); g.addColorStop(1,'rgba(111,168,12,.02)'); ctx.fillStyle=g; ctx.fill();
  line(ctx,tl,X,Y,p=>p.inside,'#6FA80C',2.2);
  line(ctx,tl,X,Y,p=>p.ins,'#2D6CDF',1.6);
  line(ctx,tl,X,Y,p=>p.outs,'#E19100',1.6);
}
function line(ctx,tl,X,Y,f,color,lw){ ctx.beginPath(); tl.forEach((p,i)=>{const x=X(p.t),y=Y(f(p)); i?ctx.lineTo(x,y):ctx.moveTo(x,y);}); ctx.strokeStyle=color; ctx.lineWidth=lw; ctx.stroke(); }

/* ── export / toast ────────────────────────────────────────────────────── */
$('exportBtn').onclick=()=>{ window.location='/api/export?t='+Date.now(); };
let toastT=null;
function toast(msg){ const el=$('toast'); el.textContent=msg; el.classList.add('show'); clearTimeout(toastT); toastT=setTimeout(()=>el.classList.remove('show'),2600); }
