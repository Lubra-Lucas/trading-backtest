/* Teste opcional de interface: node tests/check_cruzamento_browser.cjs
 * Precisa de playwright disponível ao Node e Chromium em /usr/bin/chromium.
 * Gera apenas fixtures sintéticos em diretório temporário, depois os remove.
 */
const {chromium}=require('playwright');
const {execFileSync}=require('node:child_process');
const fs=require('node:fs');
const path=require('node:path');
const os=require('node:os');
const http=require('node:http');
const assert=require('node:assert/strict');
(async()=>{
 const root=path.resolve(__dirname,'..'),tmp=fs.mkdtempSync(path.join(os.tmpdir(),'cross-browser-'));
 let browser,server;
 try {
 execFileSync('python',['-c',`
import sys
import pandas as pd
import numpy as np
sys.path.insert(0,'backtest')
import cruzamento_medias as c
rng=np.random.default_rng(2026)
times=pd.date_range('2026-09-01','2026-10-01',freq='5min',inclusive='left',tz='UTC')
x=100000*np.exp(np.cumsum(rng.normal(0,.001,len(times))))
o=np.r_[x[0],x[:-1]]
df=pd.DataFrame(dict(time=times,open=o,high=np.maximum(o,x)*1.0005,low=np.minimum(o,x)*.9995,close=x))
c.validate_candles(df)
r=c.build_report(df,dict(url='SYNTHETIC TEST FIXTURE ONLY',sha256='not market data',candles=len(df),checksum_verified=False))
c.render_report(r,sys.argv[1]+'/ready.html')
c.render_report(dict(status='blocked',candles=[],trades=[],summary=None),sys.argv[1]+'/pending.html')
`,tmp],{cwd:root});
 server=http.createServer((req,res)=>{const f={'/pending.html':'pending.html','/ready.html':'ready.html'}[req.url];if(!f){res.writeHead(404);res.end();return;}res.setHeader('Content-Type','text/html; charset=utf-8');res.end(fs.readFileSync(path.join(tmp,f)));});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const url='http://127.0.0.1:'+server.address().port;
 browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(url+'/pending.html');
 assert.match(await page.locator('#status').textContent(),/PENDENTE/);
 assert.equal(await page.locator('#trades tr').count(),0);
 assert.equal(await page.locator('#next').isDisabled(),true);
 await page.goto(url+'/ready.html');
 assert.match(await page.locator('#status').textContent(),/SINTÉTICO/);
 assert.ok(await page.locator('#trades tr').count()>20);
 assert.equal(await page.locator('#chart').isVisible(),true);
 assert.ok(await page.locator('#chart canvas').count()>0);
 assert.equal(await page.evaluate(()=>candleSeries.options().upColor),'#2563eb');
 assert.equal(await page.evaluate(()=>candleSeries.options().downColor),'#111111');
 assert.equal(await page.evaluate(()=>lcChart.options().layout.background.color),'#ffffff');
 assert.equal(await page.locator('#levels .level').count(),6);
 assert.match(await page.locator('#levels').textContent(),/R bruto/);
 assert.match(await page.locator('#trade-diagnosis').textContent(),/Por que entrou/);
 assert.equal(await page.evaluate(()=>priceLines[1].options().color),'#dc2626');
 assert.equal(await page.evaluate(()=>priceLines[0].options().lineWidth),2);
 const diagnosis=await page.locator('#trade-diagnosis').textContent();
 const first=await page.locator('#levels').textContent();
 await page.locator('#next').click();
 assert.equal(await page.locator('#trade-select').inputValue(),'1');
 assert.notEqual(await page.locator('#levels').textContent(),first);
 assert.notEqual(await page.locator('#trade-diagnosis').textContent(),diagnosis);
 await page.locator('#prev').click();assert.equal(await page.locator('#trade-select').inputValue(),'0');
 await page.locator('#trade-select').selectOption('5');
 assert.equal(await page.locator('#trades tr.selected td').first().textContent(),'#6');
 const before=await page.evaluate(()=>lcChart.timeScale().getVisibleLogicalRange());
 await page.locator('#chart').hover({position:{x:300,y:180}});await page.mouse.wheel(0,-500);await page.waitForTimeout(300);
 const after=await page.evaluate(()=>lcChart.timeScale().getVisibleLogicalRange());
 assert.notEqual(after.to-after.from,before.to-before.from);
 const box=await page.locator('#chart').boundingBox();
 await page.mouse.move(box.x+300,box.y+180);await page.mouse.down();await page.mouse.move(box.x+450,box.y+180,{steps:10});await page.mouse.up();await page.waitForTimeout(200);
 assert.notDeepEqual(await page.evaluate(()=>lcChart.timeScale().getVisibleLogicalRange()),after);
 await page.locator('#zoom-out').click();await page.locator('#zoom-in').click();
 await page.locator('#trades tr').nth(3).click();assert.equal(await page.locator('#trade-select').inputValue(),'3');
 await page.locator('#chart').hover({position:{x:300,y:200}});assert.match(await page.locator('#tooltip').textContent(),/UTC/);
 await page.setViewportSize({width:390,height:844});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth),false);
 await page.emulateMedia({colorScheme:'dark'});
 assert.ok(await page.locator('#chart canvas').count()>0);
 assert.equal(await page.evaluate(()=>candleSeries.options().upColor),'#2563eb');
 assert.equal(await page.evaluate(()=>candleSeries.options().downColor),'#111111');
 assert.equal(await page.evaluate(()=>lcChart.options().layout.background.color),'#ffffff');
 assert.deepEqual(errors,[]);
 console.log('Browser OK: pendência, identificação sintética, gráfico, entrada/saída, níveis R, tabela, navegação, zoom, tooltip e mobile. Não valida dados reais.');
 } finally {if(browser)await browser.close();if(server)await new Promise(resolve=>server.close(resolve));fs.rmSync(tmp,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exit(1)});
