const {chromium}=require('playwright'),http=require('http'),fs=require('fs'),path=require('path'),assert=require('assert/strict');
(async()=>{
 const root=path.resolve(__dirname,'..');
 const html=fs.readFileSync(path.join(root,'docs/tendencia-histerese/index.html'));
 const server=http.createServer((req,res)=>{res.setHeader('Content-Type','text/html');res.end(html)});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const p=await browser.newPage({viewport:{width:1440,height:1400}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
  await p.goto('http://127.0.0.1:'+server.address().port);
  assert.match(await p.locator('h1').textContent(),/Tendência/);
  assert.match(await p.locator('#notice').textContent(),/sem stop/);
  const data=await p.evaluate(()=>({count:D.trades.length,source:D.source,closed:D.gross_summary.closed,open:D.gross_summary.open}));
  assert.equal(data.source.checksum_verified,true);assert.equal(data.source.candles,8640);
  assert.equal(await p.locator('#trades tr').count(),data.count);
  assert.equal(await p.evaluate(()=>indicatorSeries.length),6);
  assert.equal(await p.evaluate(()=>candleSeries.options().upColor),'#2563eb');
  assert.equal(await p.evaluate(()=>candleSeries.options().downColor),'#111111');
  assert.match(await p.locator('#trade-diagnosis').textContent(),/faixas/);
  assert.match(await p.locator('#levels').textContent(),/referência/);
  const prior=await p.locator('#trade-diagnosis').textContent();await p.locator('#next').click();
  assert.equal(await p.locator('#trade-select').inputValue(),'1');assert.notEqual(await p.locator('#trade-diagnosis').textContent(),prior);
  await p.locator('#show-bands').uncheck();assert.equal(await p.evaluate(()=>indicatorSeries[2].options().visible),false);
  await p.locator('#show-bands').check();assert.equal(await p.evaluate(()=>indicatorSeries[2].options().visible),true);
  const before=await p.evaluate(()=>lcChart.timeScale().getVisibleLogicalRange());
  await p.locator('#chart').hover({position:{x:300,y:180}});await p.mouse.wheel(0,-500);await p.waitForTimeout(250);
  const after=await p.evaluate(()=>lcChart.timeScale().getVisibleLogicalRange());assert.ok(after.to-after.from<before.to-before.from);
  await p.locator('#chart').hover({position:{x:250,y:180}});assert.match(await p.locator('#tooltip').textContent(),/Estado/);
  if(data.open){await p.locator('#trade-select').selectOption(String(data.count-1));assert.match(await p.locator('#trade-diagnosis').textContent(),/fora das métricas/);}
  await p.locator('#trade-select').selectOption('0');await p.screenshot({path:path.join(root,'work/tendencia-real.png')});
  await p.setViewportSize({width:390,height:844});await p.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  assert.deepEqual(errors,[]);console.log('Tendência no navegador: dados reais, seis linhas, faixas alternáveis, navegação, zoom, estado no cursor, R de referência e mobile OK.');
 }finally{await browser.close();server.close();}
})().catch(e=>{console.error(e);process.exit(1)});
