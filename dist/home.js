'use strict';
const PortfolioHome=(()=>{
 let catalog=null,data=null,news=null,chosen='hadlima',handlers={},newsError='';
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
 function card(p){return '<button class="portfolio-product" type="button" data-portfolio="'+e(p.id)+'" aria-pressed="'+(p.id===chosen)+'"><span class="portfolio-product-top"><strong>'+e(p.name)+'</strong><span class="portfolio-arrow" aria-hidden="true">↗</span></span><small>'+e(p.proper||p.molecule)+'</small><span class="portfolio-stage">'+e(p.statusLabel)+'</span></button>';}
 function renderCatalog(){
  if(!catalog)return;
  el('portfolioFreshness').textContent='포트폴리오 확인 '+date(catalog.reviewedAt);
  el('portfolioNote').textContent=catalog.note;
  el('portfolioGrid').innerHTML=[['launched','US launched','미국 출시 제품'],['pipeline','Development & launch readiness','개발·출시 준비 제품']].map(([key,title,subtitle])=>{
   const ps=catalog.products.filter(p=>p.column===key),areas=[...new Set(ps.map(p=>p.area))];
   return '<section class="portfolio-column '+key+'"><div class="portfolio-column-heading"><div><p class="eyebrow">'+e(subtitle)+'</p><h2>'+e(title)+'</h2></div><span class="portfolio-count">'+ps.length+'</span></div>'+areas.map(area=>'<section class="therapy-group"><h3>'+e(area)+'</h3><div class="therapy-products">'+ps.filter(p=>p.area===area).map(card).join('')+'</div></section>').join('')+'</section>';
  }).join('');
 }
 function renderSummary(){
  const p=catalog?.products.find(p=>p.id===chosen);if(!p)return;
  el('productSummary').hidden=false;el('homeProductName').textContent=p.name;
  el('homeProductMeta').textContent=(p.proper||p.molecule)+' · '+p.area;
  el('homeProductSource').href=p.sourceUrl;el('homeProductSource').hidden=!safe(p.sourceUrl);
  if(!data){el('homeCompetitors').innerHTML='<p class="summary-empty">허가 데이터를 불러오는 중입니다.</p>';el('homeRegulatory').hidden=true;}
  else{
   const rows=competitors(data.products,p),ref=rows.find(x=>x.kind==='reference');
   const rivals=rows.filter(x=>x.kind==='biosimilar'&&!x.own);
   el('homeRegulatory').hidden=!ref;
   el('homeCompetitors').innerHTML=ref?'<p class="snapshot-scope">'+e(p.molecule)+' · Reference: '+e(p.reference)+'</p><div class="competitor-total"><strong>'+rivals.length+'</strong><span>허가된 경쟁 바이오시밀러 브랜드</span></div><div class="competitor-list">'+rows.map(x=>'<div class="competitor-row '+(x.own?'own':'')+'"><span><strong>'+e(x.brand)+'</strong><small>'+e(x.proper)+'</small></span><span class="competitor-kind">'+(x.kind==='reference'?'Originator':x.own?'Selected':'Biosimilar')+'</span></div>').join('')+'</div><p class="snapshot-footnote">Purple Book · '+date(data.purpleBookAsOf||data.purpleBookDate)+'<br>동일 molecule·reference 기준 · 자사 선택 제품 제외 수 · 허가와 출시 여부는 별개</p>':'<p class="snapshot-scope">Reference: '+e(p.reference||'해당 없음')+'</p><p class="summary-empty">현재 Regulatory 수집 범위에 없는 molecule입니다. 경쟁 제품 허가 현황은 아직 연결되지 않았습니다.</p>';
  }
  const rows=related(news?.articles||[],p.molecule);
  el('homeNews').innerHTML=!news?'<p class="summary-empty">'+e(newsError||'관련 뉴스를 불러오는 중입니다.')+'</p>':rows.length?'<p class="snapshot-scope">'+e(p.molecule)+' · 최근 수집 기사</p><div class="home-news-list">'+rows.slice(0,3).map(a=>'<article><div class="news-meta"><span>'+e(a.source)+'</span><time datetime="'+e(a.publishedAt)+'">'+date(a.publishedAt)+'</time></div><a href="'+e(a.url)+'" target="_blank" rel="noopener noreferrer">'+e(a.title)+' ↗</a></article>').join('')+'</div><p class="snapshot-footnote">뉴스 게시본 · '+date(news.updatedAt)+'</p>':'<p class="summary-empty">'+e(p.molecule)+' 관련 수집 기사가 아직 없습니다.</p>';
 }
 async function loadNews(){try{const r=await fetch('news.json',{cache:'no-store'});if(!r.ok)throw Error();news=await r.json();if(!Array.isArray(news.articles))throw Error();newsError='';}catch{news=null;newsError='뉴스 게시본을 불러오지 못했습니다. Market news에서 다시 확인해 주세요.';}renderSummary();}
 async function init(callbacks){
  handlers=callbacks;window.addEventListener('market-news-updated',event=>{news=event.detail;newsError='';renderSummary();});
  el('portfolioGrid').addEventListener('click',event=>{const id=event.target.closest('[data-portfolio]')?.dataset.portfolio;if(!id)return;chosen=id;renderCatalog();renderSummary();document.querySelector('[data-portfolio="'+id+'"]')?.focus({preventScroll:true});el('productSummary').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});});
  el('homeRegulatory').addEventListener('click',()=>{const p=catalog?.products.find(p=>p.id===chosen);if(p)handlers.openRegulatory(p)});
  el('homeAllNews').addEventListener('click',()=>{const p=catalog?.products.find(p=>p.id===chosen);if(p){MarketNews.focusMolecule(p.molecule);location.hash='news';}});
  try{const r=await fetch('portfolio.json',{cache:'no-store'});if(!r.ok)throw Error();catalog=await r.json();if(!Array.isArray(catalog.products)||!catalog.products.length)throw Error();el('homeStatus').textContent='';renderCatalog();renderSummary();}catch{el('homeStatus').textContent='포트폴리오를 불러오지 못했습니다. 페이지를 새로고침해 주세요.';}
  loadNews();
 }
 return {init,setData(d){data=d;renderSummary()},competitors,related};
})();
