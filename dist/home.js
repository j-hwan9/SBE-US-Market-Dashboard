'use strict';
const PortfolioHome=(()=>{
 let catalog=null,data=null,news=null,chosen='hadlima',handlers={},newsError='',history=null,filters={area:'',stage:'',molecule:''};
 const el=id=>document.getElementById(id),e=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const date=s=>s?new Intl.DateTimeFormat('en-US',{month:'short',day:'2-digit',year:'numeric',timeZone:'UTC'}).format(/^\d{4}-\d{2}$/.test(s)?new Date(Date.UTC(+s.slice(0,4),+s.slice(5,7),0)):new Date(s)):'미확인';
 const safe=s=>{try{return new URL(s).protocol==='https:'}catch{return false}};
 function competitors(products,p){
  const rows=products.filter(x=>x.molecule===p.molecule&&(x.kind==='reference'?x.brand.toLowerCase()===p.reference.toLowerCase():x.reference.toLowerCase()===p.reference.toLowerCase()));
  const grouped=new Map();
  for(const x of rows){const key=x.brand.toLowerCase();if(!grouped.has(key))grouped.set(key,{brand:x.brand,proper:x.proper,kind:x.kind,own:key===p.name.toLowerCase()});}
  return [...grouped.values()].sort((a,b)=>(a.kind==='reference'?-1:b.kind==='reference'?1:0)||a.brand.localeCompare(b.brand));
 }
 function related(articles,molecule){return articles.filter(a=>a.molecules?.includes(molecule)&&safe(a.url)).sort((a,b)=>b.publishedAt.localeCompare(a.publishedAt));}
 function filteredPortfolio(products,filters){return products.filter(p=>(!filters.area||p.area===filters.area)&&(!filters.stage||p.column===filters.stage)&&(!filters.molecule||p.molecule===filters.molecule));}
 function recentDays(value,days,now=new Date()){
  const d=String(value||'').slice(0,10),end=now.toISOString().slice(0,10),start=new Date(now);start.setUTCDate(start.getUTCDate()-days+1);
  return /^\d{4}-\d{2}-\d{2}$/.test(d)&&d>=start.toISOString().slice(0,10)&&d<=end;
 }
 function historyRows(history,products,portfolio){
  const scopes=new Set(portfolio.map(p=>p.molecule+'|'+p.reference.toLowerCase()));
  return (history||[]).filter(h=>!h.baseline).flatMap(h=>['added','changed','removed'].flatMap(kind=>(h.changes?.[kind]||[]).flatMap(item=>{
   const product=products.find(p=>p.id===item.id)||portfolio.find(p=>p.name.toLowerCase()===String(item.brand).toLowerCase());
   const molecule=item.molecule||product?.molecule,reference=item.reference||product?.reference;
   if(!molecule||!reference||!scopes.has(molecule+'|'+reference.toLowerCase()))return [];
   return [{type:'Regulatory',date:h.checkedAt,molecule,title:item.brand+' · '+({added:'레코드 추가',changed:'레코드 수정',removed:'레코드 삭제'}[kind]),detail:h.note||(item.fields||[]).join(', '),url:'#regulatory'}];
  }))).sort((a,b)=>String(b.date).localeCompare(String(a.date)));
 }
 function scopedNews(articles,portfolio){const molecules=new Set(portfolio.map(p=>p.molecule));return articles.filter(a=>safe(a.url)&&a.molecules?.some(m=>molecules.has(m))).sort((a,b)=>b.publishedAt.localeCompare(a.publishedAt));}
 function approvedCount(products,portfolio){const ids=new Set();for(const p of portfolio)for(const row of competitors(products,p))if(row.kind==='biosimilar')ids.add(p.molecule+'|'+row.brand.toLowerCase());return ids.size;}
 function table(headers,rows,empty){return '<table class="data-table"><thead><tr>'+headers.map(h=>'<th scope="col">'+e(h)+'</th>').join('')+'</tr></thead><tbody>'+(rows.length?rows.join(''):'<tr><td colspan="'+headers.length+'" class="empty-cell">'+e(empty)+'</td></tr>')+'</tbody></table>';}
 function intelligenceTable(rows,empty){return table(['Date / Type','Intelligence'],rows.map(r=>'<tr><td class="date-cell"><time>'+date(r.date)+'</time><small>'+e(r.type)+'</small></td><td><a href="'+e(r.url)+'"'+(safe(r.url)?' target="_blank" rel="noopener noreferrer"':'')+'>'+e(r.title)+(safe(r.url)?' ↗':'')+'</a><small>'+e(r.detail||r.molecule||'')+'</small></td></tr>'),empty);}
 function renderOverview(){
  if(!catalog)return;
  const ps=filteredPortfolio(catalog.products,filters),articles=scopedNews(news?.articles||[],ps),reg=historyRows(history,data?.products||[],ps);
  const newsRows=articles.map(a=>({type:'Market news',date:a.publishedAt,title:a.title,url:a.url,detail:a.source}));
  const kpis=[
   [data?approvedCount(data.products,ps):'—','Approved biosimilars','선택 포트폴리오의 molecule·reference 기준 · 자사 포함'],
   [history===null?'—':reg.filter(r=>recentDays(r.date,30)).length,'Tracked record changes (30d)','게시 레코드 변경 · FDA 신규 허가 건수 아님'],
   ['—','Pricing updates (30d)','가격 데이터 미연결'],
   [news?articles.filter(a=>recentDays(a.publishedAt,7)).length:'—','Market news (7d)','관련 molecule 수집 기사 · UTC 게시일 기준']
  ];
  el('homeKpis').innerHTML=kpis.map(([n,label,note])=>'<article class="kpi-card"><span>'+e(label)+'</span><strong>'+n+'</strong><small>'+e(note)+'</small></article>').join('');

 }
 function renderCatalog(){
  if(!catalog)return;
  el('portfolioFreshness').textContent='Portfolio reviewed '+date(catalog.reviewedAt);
  el('portfolioNote').textContent=catalog.note;
  const ps=filteredPortfolio(catalog.products,filters);
  el('portfolioCount').textContent=ps.length+' / '+catalog.products.length+' products';
  el('portfolioGrid').innerHTML=table(['Product / Molecule + suffix','Therapeutic area','US status'],ps.map(p=>'<tr'+(p.id===chosen?' class="selected-row"':'')+'><td><button class="portfolio-product" type="button" data-portfolio="'+e(p.id)+'" aria-pressed="'+(p.id===chosen)+'"><strong>'+e(p.name)+'</strong><small>'+e(p.proper||p.molecule)+'</small></button></td><td>'+e(p.area)+'</td><td><span class="status-label">'+(p.column==='launched'?'US launched / access':'Development / readiness')+'</span><small>'+e(p.statusLabel)+'</small></td></tr>'),'조건에 해당하는 제품이 없습니다. 필터를 변경해 주세요.');
  renderOverview();
 }
 function renderSummary(){
  const p=catalog?.products.find(p=>p.id===chosen);if(!p)return;
  el('productSummary').hidden=false;el('homeProductName').textContent=p.name;
  el('homeProductMeta').textContent=(p.proper||p.molecule)+' · '+p.area;
  el('homeProductSource').href=p.sourceUrl;el('homeProductSource').hidden=!safe(p.sourceUrl);
  if(!data){el('homeCompetitors').innerHTML='<p class="summary-empty">허가 데이터를 불러오는 중입니다.</p>';el('homeRegulatory').hidden=true;}
  else{
   const rows=competitors(data.products,p),ref=rows.find(x=>x.kind==='reference');
   const biosimilars=rows.filter(x=>x.kind==='biosimilar');
   el('homeRegulatory').hidden=!ref;
   el('homeCompetitors').innerHTML=ref?'<p class="snapshot-scope">'+e(p.molecule)+' · Reference: '+e(p.reference)+'</p><div class="competitor-total"><strong>'+biosimilars.length+'</strong><span>Approved biosimilars</span></div><div class="competitor-list">'+rows.map(x=>'<div class="competitor-row '+(x.own?'own':'')+'"><span><strong>'+e(x.brand)+'</strong><small>'+e(x.proper)+'</small></span><span class="competitor-kind">'+(x.kind==='reference'?'Originator':x.own?'Selected':'Biosimilar')+'</span></div>').join('')+'</div><p class="snapshot-footnote">Purple Book · '+date(data.purpleBookAsOf||data.purpleBookDate)+'<br>동일 molecule·reference 기준 · 자사 제품 포함 · 오리지네이터 제외 · 허가와 출시 여부는 별개</p>':'<p class="snapshot-scope">Reference: '+e(p.reference||'해당 없음')+'</p><p class="summary-empty">현재 Regulatory 수집 범위에 없는 molecule입니다. 경쟁 제품 허가 현황은 아직 연결되지 않았습니다.</p>';
  }
  const rows=related(news?.articles||[],p.molecule);
  el('homeNews').innerHTML=!news?'<p class="summary-empty">'+e(newsError||'관련 뉴스를 불러오는 중입니다.')+'</p>':rows.length?'<p class="snapshot-scope">'+e(p.molecule)+' · 최근 수집 기사</p><div class="home-news-list">'+rows.slice(0,3).map(a=>'<article><div class="news-meta"><span>'+e(a.source)+'</span><time datetime="'+e(a.publishedAt)+'">'+date(a.publishedAt)+'</time></div><a href="'+e(a.url)+'" target="_blank" rel="noopener noreferrer">'+e(a.title)+' ↗</a></article>').join('')+'</div><p class="snapshot-footnote">뉴스 게시본 · '+date(news.updatedAt)+'</p>':'<p class="summary-empty">'+e(p.molecule)+' 관련 수집 기사가 아직 없습니다.</p>';
 }
 async function loadNews(){try{const r=await fetch('news.json',{cache:'no-store'});if(!r.ok)throw Error();news=await r.json();if(!Array.isArray(news.articles))throw Error();newsError='';}catch{news=null;newsError='뉴스 게시본을 불러오지 못했습니다. Market news에서 다시 확인해 주세요.';}renderSummary();renderOverview();}
 async function init(callbacks){
  handlers=callbacks;
  for(const [id,key] of [['homeArea','area'],['homeStage','stage'],['homeMolecule','molecule']])el(id).addEventListener('change',()=>{filters[key]=el(id).value;const ps=filteredPortfolio(catalog?.products||[],filters);if(!ps.some(p=>p.id===chosen))chosen=ps[0]?.id||'';renderCatalog();el('productSummary').hidden=!chosen;renderSummary();});
  el('homeReset').addEventListener('click',()=>{filters={area:'',stage:'',molecule:''};for(const id of ['homeArea','homeStage','homeMolecule'])el(id).value='';if(!chosen)chosen='hadlima';renderCatalog();renderSummary();});window.addEventListener('market-news-updated',event=>{news=event.detail;newsError='';renderSummary();renderOverview();});
  el('portfolioGrid').addEventListener('click',event=>{const id=event.target.closest('[data-portfolio]')?.dataset.portfolio;if(!id)return;chosen=id;renderCatalog();renderSummary();document.querySelector('[data-portfolio="'+id+'"]')?.focus({preventScroll:true});el('productSummary').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});});
  el('homeRegulatory').addEventListener('click',()=>{const p=catalog?.products.find(p=>p.id===chosen);if(p)handlers.openRegulatory(p)});
  el('homeAllNews').addEventListener('click',()=>{const p=catalog?.products.find(p=>p.id===chosen);if(p){MarketNews.focusMolecule(p.molecule);location.hash='news';}});
  try{const r=await fetch('portfolio.json',{cache:'no-store'});if(!r.ok)throw Error();catalog=await r.json();if(!Array.isArray(catalog.products)||!catalog.products.length)throw Error();el('homeStatus').textContent='';for(const [id,key] of [['homeArea','area'],['homeMolecule','molecule']])el(id).innerHTML+=[...new Set(catalog.products.map(p=>p[key]))].sort().map(v=>'<option value="'+e(v)+'">'+e(v)+'</option>').join('');renderCatalog();renderSummary();renderOverview();}catch{el('homeStatus').textContent='포트폴리오를 불러오지 못했습니다. 페이지를 새로고침해 주세요.';}
  loadNews();
 }
 return {init,setData(d,h=null){data=d;history=h;renderSummary();renderOverview()},competitors,related,filteredPortfolio,recentDays,historyRows,approvedCount,scopedNews};
})();
