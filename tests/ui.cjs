const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const root=path.resolve(__dirname,'..');const els=new Map();
const document={getElementById(id){if(!els.has(id))els.set(id,{innerHTML:'',textContent:'',value:'',checked:false,hidden:false,addEventListener(){},showModal(){},close(){}});return els.get(id)}};
const context=vm.createContext({document,fetch:()=>new Promise(()=>{}),Intl,Date,console});
vm.runInContext(fs.readFileSync(path.join(root,'dist/chart.js'),'utf8'),context);
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
