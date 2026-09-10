const assert=require('node:assert/strict');
const fs=require('node:fs');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || process.argv[2] || 'playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:process.env.PLAYWRIGHT_CHANNEL || 'msedge'});
 const page=await browser.newPage();const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',route=>{
  const url=new URL(route.request().url());
  if(route.request().isNavigationRequest())return route.fulfill({body:fs.readFileSync('work/dashboard-tests/activity.html'),contentType:'text/html'});
  if(url.pathname==='/npm/chart.js')return route.fulfill({body:'window.chartConfigs=[];window.Chart=class{constructor(element,config){window.chartConfigs.push(config)}static register(){}};',contentType:'application/javascript'});
  const file='app'+url.pathname;
  if(url.pathname.startsWith('/static/')&&fs.existsSync(file))return route.fulfill({body:fs.readFileSync(file),contentType:file.endsWith('.js')?'application/javascript':'text/css'});
  return route.fulfill({body:'',contentType:'application/javascript'});
 });
 await page.goto('http://test.local/dashboard/activity');
 const expected='새 "제품" <테스트>';
 assert.equal((await page.locator('#productFilter option[value=custom_product]').textContent()).trim(),expected);
 const series=await page.evaluate(name=>window.chartConfigs[0].data.datasets.find(d=>d.label===name),expected);
 assert.deepEqual(series.data,[0,0]);
 assert.ok(series.borderColor);
 assert.equal(await page.evaluate(()=>window.chartConfigs[0].data.datasets.length),8);
 assert.deepEqual(errors,[]);
 await browser.close();console.log('Dashboard browser passed: eighth product in filter and chart, safe special-character name, no script errors.');
})().catch(e=>{console.error(e);process.exit(1)});
