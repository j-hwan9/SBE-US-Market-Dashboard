const fs=require('fs'),vm=require('vm'),assert=require('assert');
const context=vm.createContext({console,URL});vm.runInContext(fs.readFileSync('dist/home.js','utf8'),context);
context.data=JSON.parse(fs.readFileSync('dist/data.json'));context.catalog=JSON.parse(fs.readFileSync('dist/portfolio.json'));
const run=s=>vm.runInContext(s,context);
for(const p of context.catalog.products){
 assert(p.sourceUrl.startsWith('https://'));assert(p.proper);assert(p.reference!==undefined);
 if(p.column==='launched'||p.statusLabel.includes('FDA approved')){const row=context.data.products.find(x=>x.brand===p.name);assert(row,'Missing US brand: '+p.name);assert.equal(p.proper,row.proper);assert.equal(p.reference,row.reference);}
}
assert.equal(context.catalog.products.length,new Set(context.catalog.products.map(p=>p.id)).size);
const get=id=>{context.p=context.catalog.products.find(p=>p.id===id);return run('PortfolioHome.competitors(data.products,p)')};
let rows=get('hadlima');assert.equal(rows[0].brand,'Humira');assert.equal(rows.filter(p=>p.own).length,1);assert(rows.length>5);
rows=get('pyzchiva');assert.equal(rows.filter(p=>p.own).length,1,'Multi-BLA brand counted once');
rows=get('ospomyv');assert.equal(rows[0].brand,'Prolia');assert(!rows.some(x=>x.brand==='Xbryk'));
rows=get('xbryk');assert.equal(rows[0].brand,'Xgeva');assert(!rows.some(x=>x.brand==='Ospomyv'));
assert.equal(get('sb38').length,0,'ADC must not match trastuzumab');
context.news=[{title:'old',url:'https://example.org/1',publishedAt:'2026-01-01',molecules:['adalimumab']},{title:'new',url:'https://example.org/2',publishedAt:'2026-08-01',molecules:['adalimumab']},{title:'other',url:'https://example.org/3',publishedAt:'2026-09-01',molecules:['ustekinumab']}];
assert.equal(run("PortfolioHome.related(news,'adalimumab')[0].title"),'new');
console.log('Portfolio source mappings, BLA deduplication, reference scoping and recent-news selection verified.');

context.history=JSON.parse(fs.readFileSync('dist/history/index.json'));
assert.equal(run("PortfolioHome.filteredPortfolio(catalog.products,{molecule:'adalimumab'}).length"),1);
assert.equal(run("PortfolioHome.filteredPortfolio(catalog.products,{stage:'pipeline',molecule:'adalimumab'}).length"),0);
assert.equal(run("PortfolioHome.approvedCount(data.products,catalog.products.filter(p=>p.id==='hadlima'))"),get('hadlima').filter(p=>p.kind==='biosimilar').length);
assert.equal(run("PortfolioHome.approvedCount([...data.products,...data.products],catalog.products.filter(p=>p.id==='hadlima'))"),get('hadlima').filter(p=>p.kind==='biosimilar').length);
assert(run("PortfolioHome.recentDays('2026-09-03',7,new Date('2026-09-09T12:00:00Z'))"));
assert(!run("PortfolioHome.recentDays('2026-09-02',7,new Date('2026-09-09T12:00:00Z'))"));
assert(!run("PortfolioHome.recentDays('2026-09-10',7,new Date('2026-09-09T12:00:00Z'))"));
assert.equal(run("PortfolioHome.historyRows([{baseline:true,changes:{added:[{brand:'Hadlima'}]}}],data.products,catalog.products).length"),0);
assert.equal(run("PortfolioHome.scopedNews(news,catalog.products.filter(p=>p.id==='hadlima')).length"),2);
assert.equal(run("PortfolioHome.historyRows([{checkedAt:'2026-09-09',changes:{changed:[{brand:'Hadlima',id:data.products.find(p=>p.brand==='Hadlima').id}]}}],data.products,catalog.products.filter(p=>p.id==='sb38')).length"),0);
console.log('Home metrics: shared filters, brand deduplication, UTC windows, baseline exclusion and molecule scoping passed.');
