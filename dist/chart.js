'use strict';
// Comparison / vertical bar, 21+ molecules, one count measure. Zero baseline.
// Grain: distinct proprietary brand per molecule among current 351(k) records.
let marketChartInstance;
function marketCounts(products){
 const groups=new Map();
 products.filter(p=>p.kind==='biosimilar').forEach(p=>{if(!groups.has(p.molecule))groups.set(p.molecule,new Set());groups.get(p.molecule).add(p.brand.toLowerCase());});
 return [...groups].map(([molecule,brands])=>({molecule,count:brands.size})).sort((a,b)=>b.count-a.count||a.molecule.localeCompare(b.molecule));
}
function drawMarketChart(data,current,onSelect){
 const rows=marketCounts(data.products),root=document.getElementById('marketChart');
 if(marketChartInstance)marketChartInstance.destroy();
 root.innerHTML='<div class="chart-canvas-wrap"><canvas id="countCanvas" role="img" aria-label="성분별 허가 바이오시밀러 브랜드 수"></canvas></div><details class="chart-values"><summary>전체 수치 보기</summary><div class="count-values"></div></details>';
 const values=root.querySelector('.count-values');
 rows.forEach(r=>{const b=document.createElement('button');b.textContent=r.molecule+' · '+r.count;b.addEventListener('click',()=>onSelect(r.molecule));values.appendChild(b);});
 if(typeof Chart==='undefined'){root.querySelector('details').open=true;return;}
 const labelsPlugin={id:'countLabels',afterDatasetsDraw(chart){const {ctx}=chart;ctx.save();ctx.textAlign='center';ctx.fillStyle='#28384e';ctx.font='600 13px sans-serif';chart.getDatasetMeta(0).data.forEach((bar,i)=>ctx.fillText(rows[i].count,bar.x,bar.y-8));ctx.restore();}};
 marketChartInstance=new Chart(document.getElementById('countCanvas'),{type:'bar',data:{labels:rows.map(r=>r.molecule),datasets:[{label:'허가 브랜드 수',data:rows.map(r=>r.count),backgroundColor:rows.map(r=>r.molecule===current?'#6030bb':'#618ab4'),borderRadius:3,maxBarThickness:38}]},options:{responsive:true,maintainAspectRatio:false,animation:false,layout:{padding:{top:22}},plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>'허가 바이오시밀러 브랜드 '+c.raw+'개'}}},scales:{y:{beginAtZero:true,grace:2,ticks:{precision:0,font:{size:12}},title:{display:true,text:'브랜드 수'},grid:{color:'#e8edf3'}},x:{ticks:{autoSkip:false,maxRotation:48,minRotation:48,font:{size:12}},grid:{display:false}}},onClick:(e,elements)=>{if(elements.length)onSelect(rows[elements[0].index].molecule);}},plugins:[labelsPlugin]});
}
