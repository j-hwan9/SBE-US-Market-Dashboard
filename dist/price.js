'use strict';
const PriceTracker=(()=>{
 let payload=null,chart=null,loading=false,initialized=false,selected=new Set();
 const el=id=>document.getElementById(id),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const unitLabel=s=>String(s||'').trim().toLowerCase().replace(/\s+/g,' ');
 const safe=s=>{try{return new URL(s).protocol==='https:'}catch{return false}};
 const date=s=>s?new Intl.DateTimeFormat('en-US',{month:'short',day:'2-digit',year:'numeric',timeZone:'UTC'}).format(new Date(s)):'미확인';
 const month=(d=new Date())=>new Intl.DateTimeFormat('en-US',{month:'short',year:'numeric',timeZone:'Asia/Seoul'}).format(d);
 const money=n=>Number.isFinite(n)?new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',minimumFractionDigits:2,maximumFractionDigits:6}).format(n):'—';
 function brandColor(brand){const ps=[...new Map((payload?.rows||[]).filter(r=>r.molecule===el('aspMolecule').value).map(r=>[r.brand,r])).values()].sort((a,b)=>(a.kind==='reference'?-1:b.kind==='reference'?1:0)||a.brand.localeCompare(b.brand));return colors[Math.max(0,ps.findIndex(r=>r.brand===brand))%colors.length];}
 const colors=['#1428a0','#16816a','#b06420','#8055a1','#3689bc','#b44569','#737947','#684637','#346c88','#777777'];
 function filtered(rows,molecule,from,to,brands){return rows.filter(r=>r.molecule===molecule&&(!from||r.quarter>=from)&&(!to||r.quarter<=to)&&brands.has(r.brand));}
 function value(row,metric,unit){const n=metric==='paymentLimit'?row.paymentLimit:row.estimatedAsp;return Number.isFinite(n)&&(unit==='billing'||Number.isFinite(row.standardFactor))?n*(unit==='standard'?row.standardFactor:1):null;}
 function options(values,current){return values.map(v=>'<option'+(v===current?' selected':'')+' value="'+esc(v)+'">'+esc(v)+'</option>').join('');}
 function selectMolecule(){
  if(!payload)return;
  const rows=payload.rows.filter(r=>r.molecule===el('aspMolecule').value),quarters=[...new Set(rows.map(r=>r.quarter))].sort();
  el('aspFrom').innerHTML=options(quarters,quarters[Math.max(0,quarters.length-12)]);el('aspTo').innerHTML=options(quarters,quarters.at(-1));
  const products=[...new Map(rows.map(r=>[r.brand,r])).values()].sort((a,b)=>(a.kind==='reference'?-1:b.kind==='reference'?1:0)||a.brand.localeCompare(b.brand));selected=new Set(products.map(r=>r.brand));
  el('aspProducts').innerHTML=products.map((r,i)=>'<label><input type="checkbox" value="'+esc(r.brand)+'" checked><span style="color:'+brandColor(r.brand)+'">'+esc(r.brand)+(r.kind==='reference'?' · Originator':'')+'</span></label>').join('');render();
 }
 function current(){return filtered(payload?.rows||[],el('aspMolecule').value,el('aspFrom').value,el('aspTo').value,selected);}
 function render(){
  if(!payload)return;
  const from=el('aspFrom').value,to=el('aspTo').value,metric=el('aspMetric').value,unit=el('aspUnit').value;
  const rows=from>to?[]:current(),quarters=[...new Set(payload.rows.filter(r=>r.molecule===el('aspMolecule').value&&r.quarter>=from&&r.quarter<=to).map(r=>r.quarter))].sort();
  const series=[...new Map(rows.map(r=>[r.brand+'|'+r.hcpcs,r])).values()];
  const unavailable=rows.filter(r=>value(r,metric,unit)===null).length;
  const units=[...new Set(rows.map(r=>unitLabel(unit==='billing'?r.billingUnit:r.standardDose)))];
  const preliminary=rows.some(r=>r.publicationStatus==='Preliminary');
  el('aspStatus').textContent=from>to?'시작 분기가 종료 분기보다 늦습니다.':rows.length?rows.length+' records · '+units.join(' / ')+' · USD'+(preliminary?' · Preliminary 분기 포함':'')+(unavailable?' · '+unavailable+'건 계산 불가/미확인':'')+(units.length>1?' · 서로 다른 단위 포함: 단위를 맞춘 뒤 비교하세요.':''):'선택 조건에 해당하는 데이터가 없습니다.';
  el('aspExport').disabled=!rows.length;
  if(chart){chart.destroy();chart=null;}
  if(typeof Chart!=='undefined')chart=new Chart(el('aspChart'),{type:'line',data:{labels:quarters,datasets:series.map((p,i)=>({label:p.brand+' · '+p.hcpcs,data:quarters.map(q=>{const r=rows.find(r=>r.brand===p.brand&&r.hcpcs===p.hcpcs&&r.quarter===q);return r?value(r,metric,unit):null}),borderColor:brandColor(p.brand),backgroundColor:brandColor(p.brand),borderWidth:p.own?3:2,pointRadius:2,spanGaps:false,tension:0}))},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},plugins:{legend:{position:'bottom',labels:{boxWidth:12,font:{size:10}}},tooltip:{callbacks:{label:c=>c.dataset.label+': '+money(c.raw)}}},scales:{y:{beginAtZero:true,title:{display:true,text:(metric==='asp'?'Estimated ASP':'CMS Payment limit')+' · USD'},ticks:{callback:n=>'$'+n}},x:{grid:{display:false},ticks:{font:{size:10}}}}}});
  el('aspTable').innerHTML='<table class="data-table"><thead><tr>'+['Payment quarter','Product / HCPCS','Billing unit','CMS Payment limit','Estimated ASP','Add-on','Basis / Notes','Source'].map(h=>'<th scope="col">'+h+'</th>').join('')+'</tr></thead><tbody>'+rows.slice().sort((a,b)=>b.quarter.localeCompare(a.quarter)||a.brand.localeCompare(b.brand)||a.hcpcs.localeCompare(b.hcpcs)).map(r=>'<tr><td>'+esc(r.quarter)+(r.publicationStatus==='Preliminary'?'<small>Preliminary</small>':'')+'</td><td><strong>'+esc(r.brand)+'</strong><small>'+esc(r.hcpcs)+' · '+esc(r.proper)+'</small></td><td>'+esc(unit==='standard'?r.standardDose:r.billingUnit)+'<small>'+esc(unit==='standard'?'환산 용량 기준':r.unitSource)+'</small></td><td>'+money(value(r,'paymentLimit',unit))+'</td><td>'+money(value(r,'asp',unit))+'</td><td>'+(r.addonPct===null?'—':r.addonPct+'%')+'</td><td>'+esc(r.method)+'<small>'+esc(r.notes)+'</small></td><td>'+(safe(r.sourceUrl)?'<a href="'+esc(r.sourceUrl)+'" target="_blank" rel="noopener">'+(r.sourceCheckedAt?'CMS file':'기존 저장본')+' ↗</a>':'—')+'<small>'+date(r.sourceCheckedAt)+(r.publicationStatus==='Preliminary'?' · Preliminary':'')+'</small></td></tr>').join('')+(rows.length?'':'<tr><td colspan="8" class="empty-cell">표시할 데이터가 없습니다.</td></tr>')+'</tbody></table>';
 }
 function csvCell(v){let s=String(v??'');if(/^[=+\-@\t\r]/.test(s))s="'"+s;return '"'+s.replace(/"/g,'""')+'"';}
 function exportCsv(){const rows=current(),unit=el('aspUnit').value;const headers=['payment_quarter','molecule','brand','hcpcs','unit','payment_limit_usd','estimated_asp_usd','addon_pct','method','notes','source_url','source_checked_at','publication_status'];const lines=rows.map(r=>[r.quarter,r.molecule,r.brand,r.hcpcs,unit==='standard'?r.standardDose:r.billingUnit,value(r,'paymentLimit',unit),value(r,'asp',unit),r.addonPct,r.method,r.notes,r.sourceUrl,r.sourceCheckedAt,r.publicationStatus||'Archived snapshot']);const blob=new Blob(['\ufeff'+[headers,...lines].map(line=>line.map(csvCell).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='CMS-ASP-'+el('aspMolecule').value+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 async function load(){
  if(loading)return;loading=true;el('aspRefresh').disabled=true;el('aspStatus').textContent='게시본을 불러오는 중입니다.';
  try{const r=await fetch('asp.json',{cache:'no-store'});if(!r.ok)throw Error('ASP 게시본을 불러오지 못했습니다.');const next=await r.json();if(next.schemaVersion!==1||!Array.isArray(next.rows)||!next.rows.length)throw Error('ASP 데이터 형식을 확인해 주세요.');payload=next;window.dispatchEvent(new CustomEvent('cms-asp-updated',{detail:payload}));
   const old=el('aspMolecule').value,molecules=[...new Set(payload.rows.map(r=>r.molecule))].sort();el('aspMolecule').innerHTML=options(molecules,molecules.includes(old)?old:molecules.includes('Trastuzumab')?'Trastuzumab':molecules[0]);el('aspMolecule').disabled=false;
   el('aspFreshness').textContent=payload.cmsCheckedAt?'CMS 확인 '+date(payload.cmsCheckedAt)+' · '+payload.rows.length+' records':'기존 저장본 · 저장소 수정 '+date(payload.sourceRepositoryUpdatedAt)+' · CMS 재확인 전';
   el('aspCoverage').innerHTML='<p>'+esc(payload.coverage)+'</p><p>분기 범위 '+esc([...new Set(payload.rows.map(r=>r.quarter))].sort().join(', '))+'</p>'+(payload.collectionErrors?.length?'<p>일부 분기는 갱신되지 않았습니다. 해당 분기의 이전 저장본을 유지합니다.</p><ul>'+payload.collectionErrors.map(x=>'<li>'+esc(x.quarter)+': '+esc(x.error)+'</li>').join('')+'</ul>':'')+'<p><a href="'+esc(payload.sourceRepository)+'" target="_blank" rel="noopener">기존 ASP 대시보드 로직 출처 ↗</a></p>';selectMolecule();
  }catch(e){el('aspStatus').textContent=e.message+(payload?' 이전에 불러온 게시본을 유지합니다.':'');}finally{loading=false;el('aspRefresh').disabled=false;}
 }
 function open(){el('priceMonth').textContent='('+month()+')';if(!initialized){initialized=true;el('aspMolecule').addEventListener('change',selectMolecule);for(const id of ['aspFrom','aspTo','aspMetric','aspUnit'])el(id).addEventListener('change',render);el('aspProducts').addEventListener('change',e=>{if(e.target.type!=='checkbox')return;e.target.checked?selected.add(e.target.value):selected.delete(e.target.value);render()});el('aspRefresh').addEventListener('click',load);el('aspExport').addEventListener('click',exportCsv);load();}else if(chart)chart.resize();}
 return{open,filtered,value,month,csvCell};
})();
