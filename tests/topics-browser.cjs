const {chromium}=require('/tmp/dashboard-browser-check/node_modules/playwright');
const fs=require('fs'),assert=require('assert');
(async()=>{
 const payload=JSON.parse(fs.readFileSync('dist/news.json'));
 const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1280,height:960}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8765/#news');
 await page.locator('#newsMolecules input[value="Policy"]').waitFor();
 await page.locator('#newsRange').selectOption('all');
 for(const topic of ['Market overall','Policy']){
  await page.locator('#newsClear').click();
  await page.locator('#newsMolecules input[value="'+topic+'"]').check();
  const expected=payload.articles.filter(a=>(a.topics||[]).includes(topic)).length;
  assert(expected>0,'No actual articles collected for '+topic);
  assert.equal(await page.locator('#newsResultCount').innerText(),expected+' articles');
  for(const card of await page.locator('.news-card').all())assert((await card.innerText()).includes(topic));
 }
 await page.locator('#newsMolecules input[value="adalimumab"]').check();
 const expected=payload.articles.filter(a=>(a.topics||[]).includes('Policy')||a.molecules.includes('adalimumab')).length;
 assert.equal(await page.locator('#newsResultCount').innerText(),expected+' articles');
 await page.locator('#newsClear').click();assert.equal(await page.locator('#newsResultCount').innerText(),payload.articles.length+' articles');
 await page.setViewportSize({width:390,height:844});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1));
 await page.locator('.section-tabs a[href="#home"]').click();
 await page.locator('.competitor-row').first().waitFor();
 assert.equal(await page.locator('#homeProductName').innerText(),'Hadlima');
 assert.equal(errors.length,0,errors.join('\n'));
 console.log('Actual news topic filters, overlapping OR selection, reset, mobile and Home verified.');await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
