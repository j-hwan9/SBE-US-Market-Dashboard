const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const A=require('../dist/analytics.js');
assert.equal(A.route('#admin'),null);assert.equal(A.route(''),'home');assert.equal(A.route('#missing'),'home');assert.equal(A.route('#prices'),'prices');
for(const kind of ['summary','daily','tabs','devices','sources']){
 const body=A.reportBody(kind,'7');assert.deepEqual(body.dateRanges,[{startDate:'7daysAgo',endDate:'yesterday'}]);
 assert.equal(body.dimensionFilter.andGroup.expressions[0].filter.stringFilter.value,'j-hwan9.github.io');
 assert.equal(body.dimensionFilter.andGroup.expressions[1].filter.stringFilter.value,'/SBE-US-Market-Dashboard/tab/');
}
assert.equal(A.reportBody('summary','30').dateRanges[0].startDate,'30daysAgo');assert.equal(A.reportBody('summary','today').dateRanges[0].endDate,'today');
assert.equal(A.reportBody('summary','7').dimensions,undefined); // Unique users for whole range, not sum of day rows.
assert.deepEqual(A.unpack({rows:[{dimensionValues:[{value:'20260915'}],metricValues:[{value:'2'},{value:'3'}]}]}),[{label:'20260915',values:[2,3]}]);
async function tracking(config,hash='',hostname=A.HOST){
 const scripts=[],handlers={},location={hash,hostname,pathname:A.BASE};
 const window={addEventListener:(k,v)=>handlers[k]=v};
 const context=vm.createContext({window,location,document:{createElement:()=>({}),head:{append:s=>scripts.push(s)}},fetch:async()=>({ok:true,json:async()=>config}),Date,console});
 vm.runInContext(fs.readFileSync('dist/analytics.js','utf8'),context);await window.DashboardAnalytics.ready;
 return {window,location,scripts,change:hash=>{location.hash=hash;handlers.hashchange();},events:()=>Array.from(window.dataLayer||[]).filter(e=>e[0]==='event')};
}
(async()=>{
 let t=await tracking({});assert.equal(t.scripts.length,0);
 t=await tracking({measurementId:'G-TEST123'},'#admin');assert.equal(t.scripts.length,0);
 t.change('#home');assert.equal(t.events().length,1);assert.equal(t.scripts.length,1);
 t.change('#home');assert.equal(t.events().length,1);t.change('#news');assert.equal(t.events().length,2);
 assert.equal(t.events()[1][2].page_location,'https://j-hwan9.github.io/SBE-US-Market-Dashboard/tab/news');
 t.change('#admin');assert.equal(t.events().length,2);assert.equal(t.window['ga-disable-G-TEST123'],true);
 t.change('#news');assert.equal(t.events().length,3);assert.equal(t.window['ga-disable-G-TEST123'],false);
 t=await tracking({measurementId:'G-TEST123'},'#home','localhost');assert.equal(t.scripts.length,0);
 console.log('Admin analytics: dates, property scope, distinct users, sanitized routes, deduplicated views, admin exclusion, unconfigured/local no tracking passed.');
})().catch(e=>{console.error(e);process.exit(1)});
