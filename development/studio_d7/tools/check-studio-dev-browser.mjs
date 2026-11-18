import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {existsSync, mkdirSync} from 'node:fs';
import {createRequire} from 'node:module';
import {resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';

const require = createRequire(import.meta.url);
const {chromium} = require(process.env.STUDIO_PLAYWRIGHT || 'playwright');
const dist = fileURLToPath(new URL('../dist/', import.meta.url));
const screenshots = fileURLToPath(new URL('../.cache/studio-dev-browser/', import.meta.url));
mkdirSync(screenshots,{recursive:true});
const origin = 'https://studio.test', repo = 'https://github.com/semishsvk/OpenRemaster-Framework';
const oldId = 'a'.repeat(32), scope = 'b'.repeat(64), commit = 'c'.repeat(40);
const bytes = Buffer.from('DEV ZIP browser fixture'), digest = createHash('sha256').update(bytes).digest('hex');
const tag = `studio-dev-${commit.slice(0,12)}-123-1`, filename = `OpenRemaster-Studio-DEV-windows-x64-${commit.slice(0,12)}.zip`;
const preview = {draft:false,prerelease:true,tag_name:tag,target_commitish:commit,published_at:'2026-11-18T07:51:39Z',html_url:`${repo}/releases/tag/${tag}`,body:'Fixture release notes',assets:[{name:filename,size:bytes.length,digest:`sha256:${digest}`,browser_download_url:`${repo}/releases/download/${tag}/${filename}`}]};
const browser = await chromium.launch({executablePath:process.env.STUDIO_BROWSER || undefined,headless:true,chromiumSandbox:true,args:['--disable-background-networking','--disable-component-update']});
try {
  for (const viewport of [{width:1280,height:800},{width:390,height:844}]) {
    const context = await browser.newContext({viewport,offline:true,serviceWorkers:'block'});
    const page = await context.newPage(), errors = [], unexpected = [], commands = [];
    let available = false, state = 'STARTED', operation = oldId, failNetwork = false, remoteCalls = 0;
    page.setDefaultTimeout(10000);
    page.on('pageerror',error=>errors.push(error.message));
    await page.exposeFunction('testNative',async(command,args)=>{
      commands.push({command,args});
      if(command==='studio_capabilities') return {schema:'OpenRemaster.StudioCapabilities.v1',worker_compiled:available,worker_ready:available,worker_scope:available?scope:null,reason:available?'Pinned DEV broker available':'Portable UI build; DEV worker support requires a commissioned HomePC build.',production_go:false};
      if(command==='studio_open_release') return;
      assert.equal(command,'dev_worker_call');
      const request=args.request;
      assert.equal(request.scenario,'build_studio_dev');
      if(request.action==='submit') {
        operation=request.operation_id;
        const saved=await page.evaluate(key=>JSON.parse(localStorage.getItem(key)),`orf-studio-operation-v2-${scope}`);
        assert.equal(saved.operation,operation);
        return JSON.stringify({schema:'OpenRemaster.DevWorkflowResult.v1',state:'REQUESTED',operation_id:operation,production_go:false,independent_authority:false,engine:'unsigned-studio-dev-build',dev_receipt_verified:true,automatic_retry:false});
      }
      assert.equal(request.action,'status');assert.equal(request.operation_id,operation);
      return JSON.stringify({schema:'OpenRemaster.DevWorkflowResult.v1',state,operation_id:operation,production_go:false,independent_authority:false,engine:'unsigned-studio-dev-build',dev_receipt_verified:true,automatic_retry:false,launch_count:1,reason:state==='HOLD'?'Fixture failure needs review':undefined,ack:{operation_id:operation},commit:state==='COMMITTED'?{operation_id:operation}:null,worker:state==='COMMITTED'?{success:true,owned_tree_stopped:true,wrapper_exit:0,artifacts:{studio_exe:'C:/DEV/Studio.exe',studio_exe_sha256:digest}}:undefined,logs:{'stdout.log':'Compiling Studio fixture','stderr.log':''}});
    });
    await page.addInitScript(()=>{window.__TAURI_INTERNALS__={invoke:(command,args)=>window.testNative(command,args)};});
    await context.route('**/*',async route=>{
      const url=new URL(route.request().url());
      if(url.origin==='https://api.github.com') {
        remoteCalls++;
        assert.equal(route.request().method(),'GET');
        if(failNetwork) return route.fulfill({status:503,contentType:'application/json',body:'{}'});
        if(url.pathname.endsWith('/releases')) return route.fulfill({contentType:'application/json',body:JSON.stringify([preview])});
        if(url.pathname.endsWith('/actions/runs/123')) return route.fulfill({contentType:'application/json',body:JSON.stringify({id:123,head_sha:commit,event:'push',path:'.github/workflows/studio-windows-dev.yml',status:'completed',conclusion:'success'})});
      }
      const file=resolve(dist,`.${decodeURIComponent(url.pathname==='/'?'/index.html':url.pathname)}`);
      if(url.origin===origin && file.startsWith(`${resolve(dist)}${sep}`) && existsSync(file)) return route.fulfill({path:file});
      unexpected.push(url.href);await route.abort();
    });
    try {
      await page.goto(origin+'/#buildlab');
      const worker=page.getByRole('region',{name:'Studio DEV operation'});
      await worker.getByText('Portable UI build; DEV worker support requires a commissioned HomePC build.',{exact:true}).waitFor();
      assert.equal(await worker.getByTestId('dev-run').isDisabled(),true);
      assert.equal(commands.some(call=>call.command==='dev_worker_call'),false);
      assert.equal(remoteCalls,0);

      await page.goto(origin+'/#settings');
      const releases=page.getByRole('region',{name:'Studio DEV releases'});
      await releases.getByRole('button',{name:'Check DEV releases'}).click();
      await releases.getByText('CI passed for this source commit',{exact:true}).waitFor();
      assert.equal(await releases.getByRole('link',{name:'Download Windows DEV ZIP'}).getAttribute('href'),preview.assets[0].browser_download_url);
      await releases.getByLabel('Verify downloaded ZIP').setInputFiles({name:filename,mimeType:'application/zip',buffer:bytes});
      await releases.getByText('Checksum matches GitHub release metadata.',{exact:false}).waitFor();
      await page.screenshot({path:resolve(screenshots,`releases-${viewport.width}.png`),fullPage:true});
      await releases.getByLabel('Verify downloaded ZIP').setInputFiles({name:filename,mimeType:'application/zip',buffer:Buffer.from('tampered')});
      await releases.getByText('Checksum mismatch.',{exact:false}).waitFor();
      failNetwork=true;
      await releases.getByRole('button',{name:'Check DEV releases'}).click();
      await releases.getByText('Release check failed.',{exact:false}).waitFor();
      assert.equal(await releases.getByRole('link',{name:'Download Windows DEV ZIP'}).count(),0);

      available=true;
      await page.evaluate(id=>localStorage.setItem('orf-unified-dev-build-operation',id),oldId);
      await page.goto(origin+'/#buildlab');
      await worker.getByText('Building',{exact:true}).waitFor();
      await worker.getByText('stdout.log · last 8 KiB',{exact:true}).click();
      await worker.getByText('Compiling Studio fixture',{exact:true}).waitFor();
      await page.reload();
      await worker.getByText('Building',{exact:true}).waitFor();
      assert.equal(commands.filter(call=>call.args?.request?.action==='submit').length,0);
      assert.ok(commands.filter(call=>call.args?.request?.action==='status').length>=2);
      state='COMMITTED';
      await worker.getByRole('button',{name:'Refresh build status'}).click();
      await worker.getByText('Build complete',{exact:true}).waitFor();
      await worker.getByText('C:/DEV/Studio.exe',{exact:true}).waitFor();
      await worker.getByRole('button',{name:'Build a DEV candidate'}).click();
      await worker.getByText('Request sent · waiting for saved acknowledgment',{exact:true}).waitFor();
      assert.notEqual(operation,oldId);
      assert.equal(await worker.getByTestId('dev-run').isDisabled(),true);
      await page.reload();
      await worker.getByText('Build complete',{exact:true}).waitFor();
      assert.equal(commands.filter(call=>call.args?.request?.action==='submit').length,1);
      state='HOLD';
      await worker.getByRole('button',{name:'Refresh build status'}).click();
      await worker.getByText('Held for review',{exact:true}).waitFor();
      await worker.getByText('Reason: Fixture failure needs review',{exact:true}).waitFor();
      assert.equal(await worker.getByTestId('dev-run').isDisabled(),true);
      await page.screenshot({path:resolve(screenshots,`operation-${viewport.width}.png`),fullPage:true});
      assert.deepEqual(unexpected,[]);assert.deepEqual(errors,[]);
      console.log(`PASS ${viewport.width}x${viewport.height}: capabilities, release/CI identity, local file checksums, offline clearing, durable restore and single submit`);
    } finally {await context.close();}
  }
} finally {await browser.close();}
