'use strict';
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const unique=a=>[...new Set(a.filter(Boolean))];
let LATEST_DATA, DATA, selected=[], molecule='', search='', referenceName='', HISTORY=[], CONFIG={};
let historyRequest=0;
const label=p=>p.labels?.[0];
const missing=t=>`<span class="missing">${esc(t||'PI 미확보')}</span>`;
const paragraphs=(a,limit=2)=>{
 if(!a?.length)return missing('PI에 명시되지 않음 / 미확인');
 const render=x=>`<p>${esc(x)}</p>`;
 return `<div class="cell-text">${a.slice(0,limit).map(render).join('')}${a.length>limit?`<details><summary>전체 조건 보기 · ${a.length-limit}개 추가</summary><div class="detail-content">${a.slice(limit).map(render).join('')}</div></details>`:''}</div>`;
};
const renderLines=(a,limit=4)=>paragraphs(a,limit);
const piField=(p,fn)=>label(p)?fn(label(p)):null;
const section=(l,k)=>l.sections?.[k]||[];
function norm(s,p){
 let v=String(s).toLowerCase().replaceAll(p.brand.toLowerCase(),'[product]').replaceAll(p.proper.toLowerCase(),'[molecule]');
 return v.replace(/\s+/g,' ').trim();
}
function storageSubset(l,re){return unique([...(l.storage||[]),...section(l,'supplied').filter(x=>re.test(x))].filter(x=>re.test(x)));}
function cold(l){return storageSubset(l,/refriger|2\s*°?\s*c|2\s*°?\s*to\s*8|36\s*°?\s*f|expiration|expiry/i);}
function room(l){return unique([...(l.storage||[]),...section(l,'supplied'),...section(l,'dosage')].filter(x=>/room[ -]*temperature|ambient|temperatures? between (20|25|30)|out of the refrigerator|outside.*refriger|unrefriger/i.test(x)&&/hour|day|week|month|stor|discard/i.test(x)&&!/^diluted|^the diluted|^after reconstitution/i.test(x)));}
function prep(l){return unique([...section(l,'dosage'),...section(l,'storage'),...section(l,'supplied')].filter(x=>/reconstitut|dilut|prepared solution/i.test(x)&&/stor|hour|day|temperatur|immediat|refriger/i.test(x)));}
function ingredients(l){
 if(l.products?.length)return l.products.map(x=>{
  const found=x.inactive.filter(i=>/sorbitol/i.test(i.name));
  return `${x.productNdc} · ${x.active.map(a=>a.quantity).join(', ')} · ${x.forms.filter(f=>!['CARTON','PACKAGE','BOX'].includes(f)).join(' / ')}\n${found.length?'Sorbitol 함유: '+found.map(i=>i.quantity||'함량 미기재').join(', '):x.inactive.length?'Sorbitol 미등재 (SPL 첨가제 목록)':'첨가제 정보 미확인'}`;
 });
 const d=section(l,'description');const found=d.filter(x=>/sorbitol/i.test(x));return found.length?found:d.length?['Sorbitol 명시 여부: 아래 PI 조성 확인 (free로 판정하지 않음)',...d]:[];
}
function ndcs(l){
 if(l.products?.length)return l.products.map(x=>({title:unique([x.active.map(a=>a.quantity).join(', '),x.forms.filter(f=>!['CARTON','PACKAGE','BOX'].includes(f)).join(' / ')]).join(' · '),ndcs:unique(x.packages.map(y=>y.ndc)),product:x.productNdc}));
 return [];
}
const dateLines=p=>unique(p.presentations.map(r=>`${formatDate(r['Approval Date'])} · ${r.Strength} · ${r['Product Presentation']}`));
const licenseLines=p=>unique(p.presentations.map(r=>`${r['License Type'].replace('351(k) ','')} · ${r.Strength} · ${r['Product Presentation']}${r['Inter. Approval Date']?' · IC 승인 '+formatDate(r['Inter. Approval Date']):''}`));
const fields=[
 {section:'REGULATORY',key:'proper',title:'Molecule + suffix',get:p=>p.proper,render:v=>esc(v)},
 {key:'bla',title:'BLA number',get:p=>p.bla,render:v=>esc(v)},
 {key:'approval',title:'Approval date',note:'presentation별 허가일',get:dateLines,render:renderLines},
 {key:'interchange',title:'Interchangeability',note:'지정된 reference product에 대한 상태',get:licenseLines,render:renderLines},
 {key:'manufacturer',title:'Manufacturer / applicant',note:'Purple Book applicant와 PI 표기를 구분',get:p=>['Purple Book applicant: '+p.applicant,...(label(p)?.manufacturerText||[]),...(label(p)?.labelOrganizations||[]).map(x=>'PI labeler: '+x)],render:renderLines},
 {key:'marketing',title:'Marketing / licensure',get:p=>unique(p.presentations.map(r=>`${r['Marketing Status']} · ${r.Licensure} · ${r.Strength} · ${r['Product Presentation']}`)),render:renderLines},
 {section:'PRESENTATION & DEVICE',key:'presentation',title:'Presentation',get:p=>unique(p.presentations.map(r=>`${r['Product Presentation']} · ${r['Dosage Form']} · ${r['Route of Administration']}`)),render:renderLines},
 {key:'strength',title:'Strength / concentration',note:'제품 함량·농도, 투여용량과 구분',get:p=>unique(p.presentations.map(r=>`${r.Strength} · ${r['Product Presentation']}`)),render:renderLines},
 {key:'ndc',title:'NDC / package',note:'라벨에 기재된 package NDC · 판매 여부와 별개',get:p=>piField(p,l=>ndcs(l).length?ndcs(l):section(l,'supplied').filter(x=>/\d{4,5}-\d{3,4}-\d{1,2}|NDC pending|NDC X/i.test(x))),render:v=>typeof v?.[0]==='object'?`<div class="cell-text">${v.slice(0,3).map(renderPackage).join('')}${v.length>3?`<details><summary>전체 ${v.length}개 구성 보기</summary><div class="detail-content">${v.slice(3).map(renderPackage).join('')}</div></details>`:''}</div>`:paragraphs(v)},
 {key:'needle',title:'Needle / included',note:'제형별 Gauge · 제품 포함 여부 · PI 명시 기준',get:p=>label(p)?PIFacts.needle(p):null,render:renderFacts},
 {key:'indications',title:'Approved indications',note:'PI §1 · 연령 및 사용 제한 포함',get:p=>piField(p,l=>section(l,'indications')),render:v=>paragraphs(v,3)},
 {section:'STORAGE & MATERIALS',key:'cold',title:'2–8°C / refrigerated',note:'PI 우선 · FDA letter는 문서 당시 dating period',get:coldFacts,render:renderFacts},
 {key:'room',title:'Room-temperature stability',note:'온도 · 보관기간',get:p=>label(p)?PIFacts.storage(p,'room'):null,render:renderFacts},
 {key:'prep',title:'조제·개봉 후 stability',note:'온도 · 보관기간 · 투여시간 포함 여부',get:p=>label(p)?PIFacts.storage(p,'prep'):null,render:renderFacts},
 {key:'sorbitol',title:'Sorbitol status',note:'함유 / SPL 미등재 / 미확인',get:p=>piField(p,ingredients),render:v=>paragraphs(v,2)},
 {key:'latex',title:'Latex / natural rubber',note:'용기·needle cap·device별 PI 명시 범위',get:p=>piField(p,l=>l.latex),render:paragraphs},
 {section:'EVIDENCE',key:'evidence',title:'PI source / version',get:p=>(p.constituents||[p]).flatMap(q=>label(q)?['BLA '+q.bla+' · '+(label(q).provider||'DailyMed'),'게시일 '+formatDate(label(q).published_date),label(q).spl_version?'SPL version '+label(q).spl_version:'FDA PI','확인일 '+formatDate(q.piCheckedAt||DATA.retrievedAt)]:[]),render:renderLines}
];
function coldFacts(p){
 const parts=p.constituents||[p];
 return parts.flatMap(q=>{
  const rows=label(q)?PIFacts.storage(q,'cold'):[];
  const hasPeriod=rows.some(r=>/months?/i.test(r.value)&&!/재냉장|조제|희석|개봉 후/.test(r.scope+' '+r.detail));
  if(hasPeriod)return rows;
  const letter=q.approvalLetter, facts=letter?.facts||[];
  const extra=facts.map(f=>({scope:'FDA letter 당시 · '+f.scope,value:f.temperature+' · '+f.months+' months',detail:(f.basis==='from manufacture'?'제조일 기준 · ':'')+formatDate(f.documentDate)+(letter.status==='unavailable'||letter.status==='partial'?' · 최신 확인 일부 제한':''),sourceUrl:f.documentUrl,evidence:f.evidence}));
  return [...rows,...extra];
 });
}
function renderFacts(rows){return rows?.length?'<div class="fact-list">'+rows.map(r=>`<div class="fact-item"><span>${esc(r.scope)}</span><strong>${esc(r.value)}</strong>${r.detail?`<small>${esc(r.detail)}</small>`:''}${r.sourceUrl&&/^https:\/\/www\.accessdata\.fda\.gov\//.test(r.sourceUrl)?`<a class="fact-source" href="${esc(r.sourceUrl)}" target="_blank" rel="noopener">Approval letter ↗</a>`:''}</div>`).join('')+'</div>':missing('PI 명시 없음 / 해당 조건 미확인');}
function formatDate(s){
 if(!s)return '미기재';
 let value=String(s).trim(),m;
 if(/^\d{8}$/.test(value))value=value.slice(0,4)+'-'+value.slice(4,6)+'-'+value.slice(6,8);
 if((m=value.match(/^(\d{1,2})-([A-Za-z]{3})-(\d{2})$/))){const yy=+m[3];value=m[2]+' '+m[1]+', '+(yy>60?1900+yy:2000+yy);}
 if((m=value.match(/^([A-Za-z]{3})\s+(\d{1,2}),?\s+(\d{4})$/))){const mo=['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'].indexOf(m[1].toLowerCase());if(mo>=0)value=new Date(Date.UTC(+m[3],mo,+m[2])).toISOString();}
 if(/^\d{4}-\d{2}$/.test(value)){const [y,mo]=value.split('-').map(Number);value=new Date(Date.UTC(y,mo,0)).toISOString();}
 const date=new Date(value.length===10&&/^\d{4}-/.test(value)?value+'T00:00:00Z':value);
 return Number.isNaN(date.getTime())?String(s):new Intl.DateTimeFormat('en-US',{month:'short',day:'2-digit',year:'numeric',timeZone:'UTC'}).format(date);
}
function renderPackage(x){return `<div class="package"><strong>${esc(x.title)}</strong><span class="ndc">${esc(x.ndcs.length?x.ndcs.join(' / '):x.product+' (product NDC만 기재)')}</span></div>`;}
function result(f,ps){
 const values=ps.map(p=>f.get(p));
 const known=values.map(v=>v!==null&&v!==undefined&&(!Array.isArray(v)||v.length>0));
 const canonical=values.map((v,i)=>known[i]?norm(typeof v==='string'?v:JSON.stringify(v,(k,val)=>k==='evidence'?undefined:val),ps[i]):null);
 const distinct=unique(canonical);
 return {values,known,diff:distinct.length>1,unknown:known.some(k=>!k)};
}
function originator(){
 const group=DATA.products.filter(p=>p.kind==='reference'&&p.molecule===molecule&&p.brand===referenceName);
 if(!group.length)return null;
 if(group.length===1)return group[0];
 const ls=group.map(label).filter(Boolean),joined={...ls[0],sections:{}};
 for(const k of ['indications','dosage','strengths','description','supplied','storage'])joined.sections[k]=unique(ls.flatMap(l=>section(l,k)));
 for(const k of ['storage','latex','labelOrganizations','manufacturerText'])joined[k]=unique(ls.flatMap(l=>l[k]||[]));
 joined.products=ls.flatMap(l=>l.products||[]);joined.title=group[0].brand+' · '+ls.length+' PI documents';
 return {...group[0],id:'originator-'+group[0].brand.toLowerCase().replace(/\W/g,'-'),bla:unique(group.map(p=>p.bla)).join(' / '),presentations:group.flatMap(p=>p.presentations),labels:ls.length?[joined]:[],constituents:group};
}
function eligible(){return DATA.products.filter(p=>p.molecule===molecule&&p.kind==='biosimilar'&&p.reference.toLowerCase()===referenceName.toLowerCase());}
function chooseMolecule(name){
 molecule=name;search='';selected=[];$('search').value='';$('molecule').value=name;
 const names=unique(DATA.products.filter(p=>p.molecule===molecule&&p.kind==='reference').map(p=>p.brand)).sort();
 referenceName=names.includes(referenceName)?referenceName:names[0]||'';
 $('reference').innerHTML=names.map(n=>`<option>${esc(n)}</option>`).join('');$('reference').value=referenceName;
 $('referenceLabel').hidden=names.length<2;
 renderProducts();renderMatrix();drawMarketChart(DATA,molecule,chooseMolecule);
}
function renderProducts(){
 const ps=eligible().filter(p=>`${p.brand} ${p.proper}`.toLowerCase().includes(search.toLowerCase()));
 $('products').innerHTML=ps.map(p=>`<label class="product-option"><input type="checkbox" data-product="${esc(p.id)}" ${selected.includes(p.id)?'checked':''}><span><b>${esc(p.brand)}</b><small>${esc(p.proper)}</small><small>${esc(unique(p.presentations.map(r=>r['Route of Administration'])).join(' / '))} · BLA ${esc(p.bla)}</small></span></label>`).join('')||'<p class="muted">검색 결과가 없습니다.</p>';
 $('count').textContent=selected.length;
 $('selectionMessage').textContent=referenceName?`${referenceName}은 비교표 왼쪽에 항상 표시됩니다.`:'오리지네이터 정보를 확인하세요.';
}
function renderMatrix(){
 const origin=originator(),ps=[origin,...selected.map(id=>DATA.products.find(p=>p.id===id))].filter(Boolean);
 $('comparisonNote').textContent=`${molecule} · ${referenceName} + ${selected.length} biosimilars`;
 if(!origin){$('matrix').innerHTML='<div class="loading">오리지네이터 정보를 확인할 수 없습니다.</div>';return;}
 const results=fields.map(f=>result(f,ps)),focus=['interchange','presentation','room','sorbitol','latex','indications'];
 $('summary').innerHTML=fields.filter((f,i)=>focus.includes(f.key)&&results[i].diff).map(f=>`<span>${esc(f.title)} · 표기 차이</span>`).join('')+(!selected.length?'<span>비교할 바이오시밀러를 선택하세요. 선택 수 제한은 없습니다.</span>':'');
 let html=`<table style="width:calc(var(--label-width) + ${ps.length*290}px)"><colgroup><col style="width:var(--label-width)">${ps.map(()=>'<col style="width:290px">').join('')}</colgroup><thead><tr><th><span class="eyebrow">COMPARE</span><br>비교 항목<span class="small-note">PI 발췌·요약 기준<br>차이 ≠ 임상적 우열</span></th>${ps.map((p,i)=>`<th class="product-heading ${i===0?'originator-column':''}">${i?`<button class="remove" data-remove="${esc(p.id)}" aria-label="${esc(p.brand)} 비교에서 제외">×</button>`:''}<span class="type ${i===0?'ref':''}">${i===0?'ORIGINATOR · 항상 표시':'BIOSIMILAR'}</span><b>${esc(p.brand)}</b><span class="proper">${esc(p.proper)}</span><br><button class="source-btn" data-source="${esc(p.id)}">PI · 근거 보기 ↗</button></th>`).join('')}</tr></thead><tbody>`;
 let group='',count=0;
 fields.forEach((f,i)=>{
  if(f.section)group=f.section;const r=results[i];
  if($('differences').checked&&ps.length>1&&!r.diff&&!r.unknown)return;
  if(group){html+=`<tr class="section-row"><th>${group}</th>${ps.map((_,j)=>`<td class="${j===0?'originator-column':''}"></td>`).join('')}</tr>`;group='';}
  html+=`<tr><th>${esc(f.title)}${f.note?`<span class="small-note">${esc(f.note)}</span>`:''}<span class="diffbadge">${ps.length===1?'기준 제품':r.diff?'표기 차이':r.unknown?'비교 정보 부족':'표기 일치'}</span></th>${ps.map((p,j)=>`<td class="${r.diff?'diffcell ':''}${j===0?'originator-column':''}"><div class="value">${r.known[j]?f.render(r.values[j]):missing(label(p)?'PI 미기재 / 해당 조건 미확인':'PI 미확보')}</div></td>`).join('')}</tr>`;count++;
 });
 $('matrix').innerHTML=count?html+'</tbody></table>':'<div class="loading">표기가 다른 항목이 없습니다.</div>';
}
function showDialog(title,html){$('dialogTitle').textContent=title;$('dialogBody').innerHTML=html;$('sourceDialog').showModal();$('sourceDialog').scrollTop=0;}
function sourceBody(p){
 const l=label(p),fda=`https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo=${encodeURIComponent(p.bla)}`;
 let html=`<h3>${esc(p.brand)} · BLA ${esc(p.bla)}</h3><p><a href="${esc(fda)}" target="_blank" rel="noopener">Drugs@FDA</a></p>`;
 const al=p.approvalLetter;
 if(al){html+='<div class="letter-evidence"><h4>FDA approval letter · 냉장 dating period</h4><p class="source-meta">확인일 '+esc(formatDate(al.checkedAt))+' · '+esc(al.status==='documented'?'문서 근거 확인':al.status==='partial'?'일부 문서 확인 제한':al.status==='unavailable'?'최신 확인 실패':al.status==='pi_period_available'?'PI에 기간 명시':'명시된 완제품 기간 미확인')+'</p>';
 for(const f of al.facts||[])html+='<p><strong>'+esc(f.temperature+' · '+f.months+' months')+'</strong><br>'+esc(f.scope)+'<br><a target="_blank" rel="noopener" href="'+esc(f.documentUrl)+'">FDA approval letter · '+esc(formatDate(f.documentDate))+' · p. '+esc(f.page)+' ↗</a></p><blockquote>'+esc(f.evidence)+'</blockquote>';
 if(al.facts?.length)html+='<p class="source-meta">문서 작성 당시 완제품 dating period입니다. 현재 모든 제형의 유효기간을 의미하지 않습니다. 실제 포장 유효기간을 확인하세요.</p>';html+='</div>';
 }
 if(!l)return html+missing('공식 PI 미확보');
 html+=`<p><a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.provider||'DailyMed')} 원문 PI ↗</a></p><p class="source-meta">게시일 ${esc(formatDate(l.published_date))} · ${l.spl_version?'SPL v'+esc(l.spl_version):'FDA label'}<br>PI 확인 ${esc(formatDate(p.piCheckedAt||DATA.retrievedAt))}</p>`;
 for(const [k,title] of [['indications','Indications and usage'],['dosage','Dosage and administration'],['strengths','Dosage forms and strengths'],['description','Description'],['supplied','How supplied'],['storage','Storage and handling']]){
  const a=section(l,k);if(a.length)html+=`<details class="source-section"><summary>${esc(title)}</summary>${a.map(x=>`<p>${esc(x)}</p>`).join('')}</details>`;
 }
 return html;
}
function showSource(id){const p=originator()?.id===id?originator():DATA.products.find(x=>x.id===id);if(p)showDialog(p.brand+' · 출처와 PI',(p.constituents||[p]).map(sourceBody).join(''));}
function method(){
 showDialog('데이터 기준과 업데이트',`<p><strong>Purple Book 월말 기준 ${esc(formatDate(DATA.purpleBookAsOf||DATA.purpleBookDate))}</strong><br>소스 확인 ${esc(formatDate(DATA.retrievedAt))} · ${DATA.products.length}개 BLA·제품 항목</p><p><a href="${esc(DATA.purpleBookUrl)}" target="_blank" rel="noopener">공식 Purple Book CSV</a></p><ul><li>그래프는 성분별 고유 브랜드 수입니다. 오리지네이터를 제외하며 같은 브랜드의 여러 BLA·presentation은 한 번만 셉니다. Interchangeable 제품도 포함합니다. 판매 여부와는 별개입니다.</li><li>비교표는 오리지네이터를 맨 왼쪽에 고정합니다. Denosumab처럼 reference product가 둘이면 Originator 선택으로 구분합니다. 같은 오리지네이터의 여러 BLA는 한 열에 합치고 원문은 각각 제공합니다.</li><li>수동 업데이트는 GitHub의 Refresh official sources → Run workflow에서 실행합니다. 자동 실행은 매주 월요일 06:00 KST로 설정됩니다. GitHub 연결 전에는 실행되지 않습니다.</li><li>새 CSV·PI를 확인하고 검증에 통과한 경우만 게시 데이터를 교체합니다. 오류가 발생하면 기존 게시본을 유지하고 실행 기록에 원인을 남깁니다.</li><li>조회 시점에서 과거 저장본을 열 수 있습니다. 변경 이력은 신규·제외 제품과 변경된 항목을 표시합니다. 저장을 시작하기 이전 시점의 PI는 복원한 자료가 아닙니다.</li><li>수치·날짜의 UI 표시는 MMM DD, YYYY입니다. 원문 PI 인용문은 출처 문구를 보존합니다. Purple Book은 월간 자료이므로 표시일은 해당 월말 기준일입니다.</li><li>Interchangeability는 특정 reference product·presentation에 대한 지정입니다. 다른 biosimilar끼리의 대체 가능성을 의미하지 않습니다.</li><li>PI에 없는 shelf life, sorbitol-free 또는 latex-free를 추정하지 않습니다. NDC는 해당 라벨의 포장 정보이며 현재 구매 가능 여부를 보증하지 않습니다.</li><li>문구 차이는 임상적 동등성이나 우열의 판정이 아닙니다. 조제·희석 후 조건과 미개봉 보관조건, 제품별 투여경로를 구분해서 확인하세요.</li></ul>`);
}
async function historyDialog(){
 if(!HISTORY.length)return showDialog('변경 이력','<p>첫 업데이트가 완료되면 업데이트 기록이 표시됩니다.</p>');
 showDialog('변경 이력',HISTORY.map(h=>{const d=h.changes||{added:[],removed:[],changed:[]};return `<section class="history-entry"><h3>${esc(formatDate(h.checkedAt))}${h.baseline?' · 최초 저장본':''}</h3><p class="source-meta">Purple Book 월말 기준 ${esc(formatDate(h.purpleBookDate))}</p>${h.baseline?'<p>추적 시작 기준 자료입니다.</p>':`<p>신규 ${d.added.length} · 제외 ${d.removed.length} · 변경 ${d.changed.length}</p>`}${d.added.length?'<p><strong>신규:</strong> '+d.added.map(p=>esc(p.brand+' · '+p.bla)).join(', ')+'</p>':''}${d.removed.length?'<p><strong>범위 제외:</strong> '+d.removed.map(p=>esc(p.brand+' · '+p.bla)).join(', ')+'</p>':''}${d.changed.map(p=>`<p><strong>${esc(p.brand)} · ${esc(p.bla)}</strong><br>${esc(p.fields.join(' / '))}</p>`).join('')}</section>`;}).join(''));
}
function refreshDialog(){
 const repo=CONFIG.repository;
 if(!/^[\w.-]+\/[\w.-]+$/.test(repo||''))return showDialog('업데이트 연결 준비',`<p>공식 소스를 다시 수집하는 코드와 주별 실행 설정은 준비되어 있습니다. GitHub 저장소를 연결하면 실행할 수 있습니다.</p><p>연결 후 이 버튼에서 <strong>Refresh official sources → Run workflow</strong>를 열 수 있습니다. 현재 버튼은 소스 수집을 실행하지 않습니다.</p>`);
 const url=`https://github.com/${repo}/actions/workflows/refresh.yml`;
 showDialog('공식 소스 업데이트',`<p>관리자 GitHub 계정으로 아래 페이지를 열어 <strong>Run workflow</strong>를 누르세요.</p><p><a class="action-link" href="${url}" target="_blank" rel="noopener">공식 소스 업데이트 실행 페이지 ↗</a></p><p>Purple Book·DailyMed·FDA PI를 확인하고 검증 후 자동 반영합니다. 완료 후 ‘최신 게시본 불러오기’를 누르면 됩니다. 수집 시간이 필요하며 진행·오류는 GitHub 실행 기록에서 확인할 수 있습니다.</p>`);
}
function applyDataset(data){
 if(!Array.isArray(data.products)||!data.products.length)throw Error('유효한 제품 데이터가 아닙니다.');
 DATA=data;const names=unique(data.products.map(p=>p.molecule)).sort();
 $('molecule').innerHTML=names.map(m=>`<option value="${esc(m)}">${esc(m)}</option>`).join('');$('molecule').disabled=false;
 $('snapshot').innerHTML=`Purple Book 월말 기준<br><strong>${esc(formatDate(data.purpleBookAsOf||data.purpleBookDate))}</strong><br>소스 확인 ${esc(formatDate(data.retrievedAt))}`;
 $('regulatoryFreshness').textContent='소스 확인 '+formatDate(data.retrievedAt);
 $('footerNote').textContent='공식 공개자료 기반 비교 도구 · 소스 확인 '+formatDate(data.retrievedAt)+' · 미기재 정보를 없음으로 판정하지 않습니다.';
 chooseMolecule(names.includes(molecule)?molecule:names.includes('adalimumab')?'adalimumab':names[0]);
 const first=eligible().find(p=>p.brand==='Amjevita')||eligible()[0];selected=first?[first.id]:[];renderProducts();renderMatrix();
}
async function loadLatest(){
 const ticket=++historyRequest;$('updateStatus').textContent='최신 게시본 확인 중…';
 try{
  const r=await fetch('data.json',{cache:'no-store'});if(!r.ok)throw Error('게시 데이터를 불러오지 못했습니다.');const data=await r.json();
  let history=null;try{const h=await fetch('history/index.json',{cache:'no-store'});if(h.ok){const value=await h.json();if(Array.isArray(value))history=value;}}catch{}
  if(ticket!==historyRequest)return;LATEST_DATA=data;HISTORY=history||[];applyDataset(data);if(typeof PortfolioHome!=='undefined')PortfolioHome.setData(data,history);
  $('historySelect').innerHTML='<option value="">현재 게시본</option>'+HISTORY.map((h,i)=>`<option value="${esc(h.id)}">${esc(formatDate(h.checkedAt))}${h.baseline?' · 최초 저장본':' · 저장본 '+(HISTORY.length-i)}</option>`).join('');
  $('updateStatus').textContent='게시본 확인 완료 · 소스 재수집은 업데이트 버튼에서 실행';
 }catch(e){if(ticket===historyRequest)$('updateStatus').textContent=e.message;}
}
$('products').addEventListener('change',e=>{const id=e.target.dataset.product;if(!id)return;selected=e.target.checked?unique([...selected,id]):selected.filter(x=>x!==id);renderProducts();renderMatrix();});
$('molecule').addEventListener('change',()=>chooseMolecule($('molecule').value));
$('reference').addEventListener('change',()=>{referenceName=$('reference').value;selected=[];renderProducts();renderMatrix();});
$('search').addEventListener('input',()=>{search=$('search').value;renderProducts();});
$('clear').addEventListener('click',()=>{selected=[];renderProducts();renderMatrix();});
$('selectAll').addEventListener('click',()=>{selected=eligible().map(p=>p.id);renderProducts();renderMatrix();});
$('differences').addEventListener('change',renderMatrix);
$('matrix').addEventListener('click',e=>{const b=e.target.closest('button');if(b?.dataset.remove){selected=selected.filter(x=>x!==b.dataset.remove);renderProducts();renderMatrix();}else if(b?.dataset.source)showSource(b.dataset.source);});
$('methodBtn').addEventListener('click',()=>DATA&&method());$('refreshBtn').addEventListener('click',refreshDialog);$('historyBtn').addEventListener('click',historyDialog);$('reloadBtn').addEventListener('click',loadLatest);
$('closeDialog').addEventListener('click',()=>$('sourceDialog').close());
$('historySelect').addEventListener('change',async()=>{
 const id=$('historySelect').value;if(!id)return loadLatest();const h=HISTORY.find(x=>x.id===id);if(!h||!/^history\/[A-Za-z0-9_-]+\.json$/.test(h.path))return;
 const ticket=++historyRequest;$('updateStatus').textContent='과거 저장본 불러오는 중…';
 try{const r=await fetch(h.path);if(!r.ok)throw Error('과거 저장본을 불러오지 못했습니다.');const d=await r.json();if(ticket!==historyRequest)return;applyDataset(d);$('updateStatus').textContent=formatDate(h.checkedAt)+' 저장본 조회 중';}catch(e){if(ticket===historyRequest)$('updateStatus').textContent=e.message;}
});
fetch('config.json',{cache:'no-store'}).then(r=>r.ok?r.json():{}).then(c=>CONFIG=c).catch(()=>{});
loadLatest();

function navigatePage(){
 const page=location.hash.slice(1)||'home';
 $('landingPage').hidden=page!=='home';$('regulatoryPage').hidden=page!=='regulatory';
 $('newsPage').hidden=page!=='news';if(page==='news'&&typeof MarketNews!=='undefined')MarketNews.open();
 $('pricePage').hidden=page!=='prices';
 const titles={performance:'Performance tracker'};
 $('comingPage').hidden=!titles[page];$('comingTitle').textContent=titles[page]||'';
 if(!['home','regulatory','news','prices',...Object.keys(titles)].includes(page))$('landingPage').hidden=false;
 document.querySelectorAll('.section-tabs a').forEach(a=>{if(a.hash==='#'+page)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
 if(page==='regulatory'&&DATA)drawMarketChart(DATA,molecule,chooseMolecule);
}
window.addEventListener('hashchange',navigatePage);navigatePage();
if(typeof PortfolioHome!=='undefined')PortfolioHome.init({openRegulatory(p){if(!LATEST_DATA)return;applyDataset(LATEST_DATA);$('historySelect').value='';$('updateStatus').textContent='현재 게시본';chooseMolecule(p.molecule);referenceName=p.reference;$('reference').value=p.reference;selected=eligible().filter(x=>x.brand.toLowerCase()===p.name.toLowerCase()).map(x=>x.id);renderProducts();renderMatrix();location.hash='regulatory';navigatePage();}});
