const assert=require('node:assert/strict');
const fs=require('node:fs');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || process.argv[2] || 'playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:process.env.PLAYWRIGHT_CHANNEL || 'msedge'});
 const page=await browser.newPage();
 let success=true,forceChange=false;
 await page.route('**/*',route=>{
  const url=new URL(route.request().url());
  if(url.pathname==='/login' && route.request().method()==='POST')return route.fulfill({json:{success,force_change:forceChange}});
  if(url.pathname==='/logout')return route.fulfill({body: "<script>location.replace('/login')</script>",contentType:'text/html'});
  if(route.request().isNavigationRequest()){
   const name=url.pathname==='/login'?'login':'stock';
   return route.fulfill({body:fs.readFileSync('work/multi-filter/'+name+'.html'),contentType:'text/html'});
  }
  const file='app'+url.pathname;
  if(url.pathname.startsWith('/static/')&&fs.existsSync(file))return route.fulfill({body:fs.readFileSync(file),contentType:file.endsWith('.js')?'application/javascript':'text/css'});
  return route.fulfill({json:{}});
 });
 const login=async()=>{
  await page.locator('input[name=username]').fill('test');
  await page.locator('#password').fill('test');
  await page.locator('#loginButton').click();
 };
 await page.goto('http://test.local/login');
 await page.evaluate(()=>{localStorage.setItem('sidebar_collapsed','false');localStorage.setItem('sidebar_open_menus','["inventory"]');localStorage.setItem('sidebar_open_submenus','["재고"]');});
 success=false;await login();await page.getByRole('alert').filter({hasText:'올바르지'}).waitFor();
 assert.equal(await page.evaluate(()=>localStorage.getItem('sidebar_collapsed')),'false');
 success=true;await login();await page.waitForURL('**/search');
 const assertMenusClosed=async()=>{
  assert.equal(await page.locator('.menu-group.open,.menu-parent.open,.child-menu.open').count(),0);
  assert.equal(await page.evaluate(()=>localStorage.getItem('sidebar_open_menus')),null);
  assert.equal(await page.evaluate(()=>localStorage.getItem('sidebar_open_submenus')),null);
 };
 assert.equal(await page.locator('.sidebar.collapsed').count(),0);
 assert.equal(await page.locator('#sidebarToggle').getAttribute('aria-expanded'),'true');
 await assertMenusClosed();
 const openMenus=async()=>{
  const group=page.locator('.menu-group').filter({has:page.locator('.menu-parent')}).first();
  await group.locator('.menu-title').click();
  await group.locator('.menu-parent').first().click();
  return group.getAttribute('data-menu');
 };
 const menu=await openMenus();
 await page.reload();
 assert.equal(await page.locator('.sidebar.collapsed').count(),0);
 assert.equal(await page.locator('.menu-group[data-menu="'+menu+'"].open').count(),1);
 assert.equal(await page.locator('.menu-parent.open').count(),1);
 assert.equal(await page.locator('.child-menu.open').count(),1);
 await page.goto('http://test.local/logout');await page.waitForURL('**/login');
 await login();await page.waitForURL('**/search');
 assert.equal(await page.locator('.sidebar.collapsed').count(),0);
 await assertMenusClosed();
 await openMenus();
 await page.goto('http://test.local/login?expired=1');await login();await page.waitForURL('**/search');
 assert.equal(await page.locator('.sidebar.collapsed').count(),0);
 await assertMenusClosed();
 await openMenus();
 await page.goto('http://test.local/login');forceChange=true;await login();await page.waitForURL('**/change-password');
 assert.equal(await page.evaluate(()=>localStorage.getItem('sidebar_collapsed')),'false');
 await assertMenusClosed();
 // An explicitly collapsed sidebar also retains its width preference on login.
 await page.locator('#sidebarToggle').click();
 await page.goto('http://test.local/login');forceChange=false;await login();await page.waitForURL('**/search');
 assert.equal(await page.locator('.sidebar.collapsed').count(),1);
 await assertMenusClosed();
 await browser.close();console.log('Passed: login resets internal menus only; refresh preserves groups/submenus; sidebar width remains unchanged.');
})().catch(e=>{console.error(e);process.exit(1)});
