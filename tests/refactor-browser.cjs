const {chromium}=require('/tmp/dashboard-browser-check/node_modules/playwright');
const assert=require('assert'),fs=require('fs');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8765/#home');
 await page.locator('.competitor-row').first().waitFor();
 await page.waitForFunction(()=>document.querySelector('#homeRecentNews a'));
 assert.equal(await page.locator('.portfolio-product').count(),20);
 assert.equal(await page.locator('#landingPage h1').innerText(),'US Market Overview');
 assert.equal(await page.locator('.kpi-card').count(),4);
 assert.equal(await page.locator('.kpi-card').nth(2).locator('strong').innerText(),'—');
 assert.equal(await page.locator('#homeProductName').innerText(),'Hadlima');
 await page.locator('#homeMolecule').selectOption('adalimumab');
 assert.equal(await page.locator('.portfolio-product').count(),1);
 assert.equal(await page.locator('.kpi-card strong').first().innerText(),await page.locator('.competitor-total strong').innerText());
 await page.locator('#homeStage').selectOption('pipeline');
 assert.equal(await page.locator('.portfolio-product').count(),0);assert(await page.locator('#productSummary').isHidden());
 await page.locator('#homeReset').click();assert.equal(await page.locator('.portfolio-product').count(),20);
 await page.locator('[data-portfolio="ospomyv"]').click();
 assert((await page.locator('#homeCompetitors').innerText()).includes('Prolia'));assert(!(await page.locator('#homeCompetitors').innerText()).includes('Xbryk'));
 await page.locator('[data-portfolio="pyzchiva"]').click();await page.locator('#homeRegulatory').click();
 await page.waitForURL('**/#regulatory');
 assert.equal(await page.locator('#molecule').inputValue(),'ustekinumab');assert((await page.locator('#matrix thead').innerText()).includes('Pyzchiva'));
 await page.locator('#selectAll').click();assert(Number(await page.locator('#count').innerText())>5);
 await page.locator('#matrix .source-btn').first().click();assert(await page.locator('#sourceDialog').isVisible());await page.locator('#closeDialog').click();
 fs.mkdirSync('/tmp/dashboard-shots',{recursive:true});
 const shot=async(name)=>{await page.evaluate(()=>window.scrollTo(0,0));console.log(name+'_IMAGE '+(await page.screenshot({path:'/tmp/dashboard-shots/'+name+'.jpg',type:'jpeg',quality:55})).toString('base64'));};
 await shot('REGULATORY');
 await page.locator('.section-tabs a[href="#home"]').click();await page.locator('#homeAllNews').click();await page.waitForURL('**/#news');
 await page.locator('.news-card').first().waitFor();assert(await page.locator('#newsMolecules input[value="ustekinumab"]').isChecked());
 assert.equal(await page.locator('#newsRange').inputValue(),'all');await shot('NEWS');
 await page.locator('.section-tabs a[href="#prices"]').click();await page.locator('#pricePage').waitFor({state:'visible'});assert(await page.locator('#pricePage').isVisible());assert(await page.locator('#comingPage').isHidden());await shot('PRICE');
 await page.locator('.section-tabs a[href="#home"]').click();await page.locator('[data-portfolio="hadlima"]').click();await page.waitForTimeout(500);await shot('HOME');
 await page.locator('#productSummary').scrollIntoViewIfNeeded();console.log('SUMMARY_IMAGE '+(await page.screenshot({type:'jpeg',quality:55})).toString('base64'));
 for(const width of [390,768]){
  await page.setViewportSize({width,height:844});
  for(const route of ['home','regulatory','news','prices']){
   await page.evaluate(r=>location.hash=r,route);await page.waitForTimeout(150);
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),route+' overflow at '+width);
  }
  await page.evaluate(()=>location.hash='home');await page.waitForTimeout(150);await shot('MOBILE'+width);
 }
 // Independent default news state: Market overall on, Policy off.
 await page.goto('http://127.0.0.1:8765/#news');await page.locator('#newsMolecules input[value="Policy"]').waitFor();
 assert(await page.locator('#newsMolecules input[value="Market overall"]').isChecked());assert(!(await page.locator('#newsMolecules input[value="Policy"]').isChecked()));
 await page.locator('#newsMolecules input[value="Policy"]').check();assert(await page.locator('#newsMolecules input[value="Policy"]').isChecked());
 // Unavailable history is distinct from zero; regulatory data still loads.
 await page.route('**/history/index.json',r=>r.fulfill({status:503,body:'unavailable'}));
 await page.goto('http://127.0.0.1:8765/#home');await page.locator('.competitor-row').first().waitFor();
 assert.equal(await page.locator('.kpi-card').nth(1).locator('strong').innerText(),'—');
 assert.equal(errors.length,0,errors.join('\n'));
 console.log('Verified: portfolio filters, real KPI totals, empty/unavailable data, original comparisons, sources, news links/topics, price routing, responsive widths.');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
