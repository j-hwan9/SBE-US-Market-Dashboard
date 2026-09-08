const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const root=path.resolve(__dirname,'..');const els=new Map();
const document={querySelectorAll(){return []},getElementById(id){if(!els.has(id))els.set(id,{innerHTML:'',textContent:'',value:'',checked:false,hidden:false,addEventListener(){},showModal(){},close(){}});return els.get(id)}};
const context=vm.createContext({document,location:{hash:''},window:{addEventListener(){}},fetch:()=>new Promise(()=>{}),Intl,Date,console});
vm.runInContext(fs.readFileSync(path.join(root,'dist/chart.js'),'utf8'),context);
vm.runInContext(fs.readFileSync(path.join(root,'dist/facts.js'),'utf8'),context);
vm.runInContext(fs.readFileSync(path.join(root,'dist/app.js'),'utf8'),context);
context.data=JSON.parse(fs.readFileSync(path.join(root,'dist/data.json')));
const run=code=>vm.runInContext(code,context);run('DATA=data;');
for(const [input,expected] of [['15-Nov-19','Nov 15, 2019'],['20260908','Sep 08, 2026'],['2026-08','Aug 31, 2026'],['Feb 06, 2026','Feb 06, 2026']]){context.input=input;assert.equal(run('formatDate(input)'),expected)}
run('molecule="adalimumab";referenceName="Humira";selected=eligible().map(p=>p.id);renderMatrix();');
assert.ok(run('selected.length')>5);assert.equal((els.get('matrix').innerHTML.match(/class="product-heading/g)||[]).length,run('selected.length')+1);assert.ok(els.get('matrix').innerHTML.indexOf('<b>Humira</b>')<els.get('matrix').innerHTML.indexOf('<b>Amjevita</b>'));
run('selected=[];renderMatrix()');assert.ok(els.get('matrix').innerHTML.includes('<b>Humira</b>'));assert.ok(!els.get('matrix').innerHTML.includes('data-remove="humira'));
run('molecule="denosumab";referenceName="Xgeva"');assert.ok(run('eligible().every(p=>p.reference==="Xgeva")'));run('referenceName="Prolia"');assert.ok(run('eligible().every(p=>p.reference==="Prolia")'));
run('molecule="ustekinumab";referenceName="Stelara"');assert.ok(run('originator().presentations.length')>0);assert.equal(run('originator().brand'),'Stelara');
const counts=run('marketCounts(DATA.products)');assert.equal(counts.length,new Set(context.data.products.filter(p=>p.kind==='biosimilar').map(p=>p.molecule)).size);const ada=counts.find(x=>x.molecule==='adalimumab');assert.equal(ada.count,new Set(context.data.products.filter(x=>x.kind==='biosimilar'&&x.molecule==='adalimumab').map(x=>x.brand.toLowerCase())).size);
assert.notEqual(run('norm("0.4 mg",DATA.products[0])'),run('norm("0.8 mg",DATA.products[0])'));
console.log('UI logic passed: dates, >5 products, permanent originator, reference scopes, counts, numeric differences.');

const p=brand=>context.data.products.find(p=>p.brand===brand);
context.p=p('Humira');assert.ok(run("PIFacts.needle(p).some(r=>r.scope==='Autoinjector / Pen'&&r.value==='Gauge 미기재 · 포함')"));
assert.ok(run("PIFacts.storage(p,'room').some(r=>r.value==='≤ 25°C · 14 days')"));
assert.ok(!run("PIFacts.storage(p,'cold').some(r=>/14 days/.test(r.value))"));
context.p=p('Pyzchiva');assert.ok(run("PIFacts.needle(p).some(r=>r.scope==='PFS'&&r.value.startsWith('29G · 포함'))"));
assert.ok(run("PIFacts.storage(p,'cold').some(r=>r.value.includes('60 days')&&r.detail.includes('재냉장 1회'))"));
assert.ok(run("PIFacts.storage(p,'prep').some(r=>r.value.includes('24 hours')&&r.detail.includes('냉장 후 추가'))"));
context.p=p('Eylea');assert.ok(run("PIFacts.needle(p).some(r=>r.scope==='PFS'&&r.value==='30G · 미포함')"));assert.ok(run("PIFacts.needle(p).some(r=>r.scope==='Vial kit'&&r.value.includes('18G · 포함 · Filter'))"));
context.p=p('Herceptin');assert.ok(run("PIFacts.storage(p,'cold').some(r=>r.value.includes('2–8°C'))"));
assert.ok(!run('sourceBody(p)').includes('purplebooksearch'));
assert.ok(!run('fields.some(f=>f.key==="dosage"||f.key==="storage")'));
assert.equal(els.get('landingPage').hidden,false);assert.equal(els.get('regulatoryPage').hidden,true);
run("location.hash='#regulatory';DATA=null;navigatePage()");assert.equal(els.get('regulatoryPage').hidden,false);
run("location.hash='#prices';navigatePage()");assert.equal(els.get('comingTitle').textContent,'Price tracker');
console.log('PI facts and navigation passed.');
context.p=p('Actemra');assert.ok(run("PIFacts.storage(p,'prep').some(r=>r.value==='RT (온도 미기재) · 4 hours'&&r.detail==='0.45% NaCl')"));
context.p=p('Avtozma');assert.ok(run("PIFacts.storage(p,'prep').some(r=>r.value==='2–8°C · 48 hours')"));assert.ok(!run("PIFacts.storage(p,'prep').some(r=>r.value==='≤ 30°C · 48 hours')"));
context.p=p('Bkemv');assert.ok(run("PIFacts.storage(p,'prep').some(r=>r.value.includes('64 hours'))"));assert.ok(!run("PIFacts.storage(p,'cold').some(r=>r.value.includes('64 hours'))"));
context.p=p('Lantus');assert.ok(run("PIFacts.storage(p,'room').every(r=>r.value==='≤ 30°C · 28 days')"));
context.p=p('Ospomyv');assert.ok(run("PIFacts.storage(p,'cold').some(r=>r.value==='2–8°C · 28 days')"));assert.ok(!run("PIFacts.storage(p,'cold').some(r=>r.value.includes('60 days'))"));
context.p=p('Hyrimoz');assert.ok(run("PIFacts.storage(p,'room').some(r=>r.scope.includes('20 mg/0.4 mL')&&r.value.includes('21 days'))"));
for(const q of context.data.products){context.p=q;for(const kind of ['cold','room','prep']){context.kind=kind;assert.ok(run('PIFacts.storage(p,kind).every(r=>r.scope&&r.value&&!r.value.includes("undefined"))'));}}
console.log('Mixed temperatures, re-refrigeration deadlines, storage tables, concentration scopes and all-product rendering passed.');

// New news view: inclusive UTC dates and OR across selected molecules.
context.URL=URL;
vm.runInContext(fs.readFileSync(path.join(root,'dist/news.js'),'utf8'),context);
context.articles=[{publishedAt:'2026-09-01T23:30:00Z',molecules:['adalimumab']},{publishedAt:'2026-09-02T00:00:00Z',molecules:['ustekinumab']}];
assert.equal(run("MarketNews.filtered(articles,'2026-09-01','2026-09-01',new Set()).length"),1);
assert.equal(run("MarketNews.filtered(articles,'','',new Set(['ustekinumab'])).length"),1);
assert.equal(run("MarketNews.filtered(articles,'','',new Set(['ustekinumab','adalimumab'])).length"),2);
run("location.hash='#news';navigatePage()");assert.equal(els.get('newsPage').hidden,false);assert.equal(els.get('comingPage').hidden,true);
run('DATA=data');context.p=JSON.parse(JSON.stringify(p('Amjevita')));
context.p.approvalLetter={status:'documented',facts:[{scope:'40 mg/0.8 mL',months:30,temperature:'2–8°C',basis:'from manufacture',documentDate:'2016-09-23',documentUrl:'https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2016/761024orig1s000ltr.pdf',evidence:'Test evidence'}]};
assert.ok(run("coldFacts(p).some(r=>r.value==='2–8°C · 30 months'&&r.detail.includes('Sep 23, 2016'))"));
assert.ok(run("sourceBody(p).includes('Approval')||sourceBody(p).includes('approval letter')"));
console.log('News date/molecule filters, navigation, FDA-letter evidence passed.');
