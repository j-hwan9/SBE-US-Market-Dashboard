'use strict';
const MarketNews=(()=>{
 let payload=null,loading=false,error='',range='90',selected=new Set(),visibleCount=40;
 const el=id=>document.getElementById(id);
 const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const date=s=>new Intl.DateTimeFormat('en-US',{month:'short',day:'2-digit',year:'numeric',timeZone:'UTC'}).format(new Date(s));
 const validUrl=s=>{try{return new URL(s).protocol==='https:'}catch{return false}};
 function bounds(){
  if(range==='custom')return [el('newsFrom').value,el('newsTo').value];
  if(range==='all')return ['',''];
  const end=new Date(),start=new Date(end);start.setUTCDate(start.getUTCDate()-Number(range)+1);
  return [start.toISOString().slice(0,10),end.toISOString().slice(0,10)];
 }
 function filtered(articles,from,to,molecules){
  return articles.filter(a=>{const d=a.publishedAt?.slice(0,10);return d&&(!from||d>=from)&&(!to||d<=to)&&(!molecules.size||a.molecules.some(m=>molecules.has(m)))});
 }
 function render(){
  if(!el('newsList'))return;
  el('newsRefresh').disabled=loading;
  if(!payload){el('newsList').innerHTML='<div class="news-empty">'+escape(error||'뉴스를 불러오는 중입니다.')+'</div>';return}
  const [from,to]=bounds();const invalid=from&&to&&from>to;
  const rows=invalid?[]:filtered(payload.articles,from,to,selected);
  el('newsResultCount').textContent=invalid?'시작일이 종료일보다 늦습니다.':rows.length+' articles';
  el('newsFreshness').textContent=payload.updatedAt?'게시본 업데이트 '+date(payload.updatedAt):'수집 대기';
  el('newsCoverage').textContent=payload.coverageNote||'';
  const failures=(payload.sources||[]).filter(s=>s.status!=='ok');
  el('newsStatus').textContent=error|| (failures.length?failures.length+'개 매체 일부 수집 제한 · 기존 기사는 유지됩니다.':'');
  el('newsSources').innerHTML=(payload.sources||[]).map(s=>'<span class="source-health '+(s.status==='ok'?'':'limited')+'">'+escape(s.name)+' · '+({ok:'수집 완료',partial:'일부 수집',unavailable:'접근 제한'}[s.status]||s.status)+'</span>').join('');
  el('newsList').innerHTML=rows.slice(0,visibleCount).map(a=>'<article class="news-card"><div class="news-meta"><span>'+escape(a.source)+'</span><span aria-hidden="true">·</span><time datetime="'+escape(a.publishedAt)+'">'+escape(date(a.publishedAt))+'</time>'+(a.type==='press-release'?'<span class="news-kind">보도자료</span>':'')+'</div><h2>'+(validUrl(a.url)?'<a href="'+escape(a.url)+'" target="_blank" rel="noopener noreferrer">'+escape(a.title)+' <span aria-label="새 창에서 원문 열기">↗</span></a>':escape(a.title))+'</h2><div class="news-tags">'+a.molecules.map(m=>'<button type="button" data-news-tag="'+escape(m)+'">'+escape(m)+'</button>').join('')+'</div></article>').join('')||'<div class="news-empty">'+(invalid?'기간을 다시 선택해 주세요.':'선택한 조건에 해당하는 수집 기사가 없습니다.<br>기간을 넓히거나 molecule 필터를 변경해 보세요.')+'</div>';
  el('newsMore').hidden=rows.length<=visibleCount;
  el('newsClear').textContent=selected.size?'Molecule 초기화 ('+selected.size+')':'전체 molecule';
 }
 function renderMolecules(){
  el('newsMolecules').innerHTML=(payload?.molecules||[]).map(m=>'<label class="news-molecule"><input type="checkbox" value="'+escape(m)+'" '+(selected.has(m)?'checked':'')+'><span>'+escape(m)+'</span></label>').join('');
 }
 async function load(){
  if(loading)return;loading=true;error='';render();
  try{const r=await fetch('news.json',{cache:'no-store'});if(!r.ok)throw Error('뉴스 게시본을 불러오지 못했습니다. 잠시 후 다시 불러와 주세요.');const d=await r.json();if(!Array.isArray(d.articles)||!Array.isArray(d.molecules))throw Error('뉴스 데이터 형식을 확인해야 합니다.');payload=d;renderMolecules()}
  catch(e){error=e.message}finally{loading=false;render()}
 }
 function init(){
  el('newsRange').addEventListener('change',()=>{range=el('newsRange').value;el('newsCustomDates').hidden=range!=='custom';visibleCount=40;render()});
  for(const id of ['newsFrom','newsTo'])el(id).addEventListener('change',()=>{visibleCount=40;render()});
  el('newsMolecules').addEventListener('change',e=>{if(e.target.type!=='checkbox')return;if(e.target.checked)selected.add(e.target.value);else selected.delete(e.target.value);visibleCount=40;render()});
  el('newsClear').addEventListener('click',()=>{selected.clear();visibleCount=40;renderMolecules();render()});
  el('newsList').addEventListener('click',e=>{const m=e.target.closest('[data-news-tag]')?.dataset.newsTag;if(m){selected=new Set([m]);visibleCount=40;renderMolecules();render()}});
  el('newsMore').addEventListener('click',()=>{visibleCount+=40;render()});el('newsRefresh').addEventListener('click',load);
  el('newsRun').href='https://github.com/j-hwan9/SBE-US-Market-Dashboard/actions/workflows/news.yml';
 }
 init();return {open(){if(!payload&&!loading)load();else render()},filtered};
})();
