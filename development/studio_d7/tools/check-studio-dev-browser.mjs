import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {existsSync, mkdirSync, readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';

const require = createRequire(import.meta.url);
const {chromium} = require(process.env.STUDIO_PLAYWRIGHT || 'playwright');
const dist = fileURLToPath(new URL('../dist/', import.meta.url));
const screenshots = fileURLToPath(new URL('../.cache/studio-dev-browser/', import.meta.url));
mkdirSync(screenshots,{recursive:true});
const origin = 'https://studio.test', repo = 'https://github.com/semishsvk/OpenRemaster-Framework';
const portableReason = 'This portable build contains the Studio UI. DEV worker support requires a commissioned HomePC build.';
const oldId = 'a'.repeat(32), scope = 'b'.repeat(64), commit = 'c'.repeat(40);
const bytes = Buffer.from('DEV ZIP browser fixture'), digest = createHash('sha256').update(bytes).digest('hex');
const logBytes=Buffer.from('Compiling Studio fixture\nwarning: fixture warning\nerror: retained fixture error\n'.repeat(3000));
const logSha=createHash('sha256').update(logBytes).digest('hex');
const zipBytes=Buffer.from('UEsFBgAAAAAAAAAAAAAAAAAAAAAAAA==','base64'),zipSha=createHash('sha256').update(zipBytes).digest('hex');
const tag = `studio-dev-${commit.slice(0,12)}-123-1`, filename = `OpenRemaster-Studio-DEV-windows-x64-${commit.slice(0,12)}.zip`;
const preview = {draft:false,prerelease:true,tag_name:tag,target_commitish:commit,published_at:'2026-11-18T07:51:39Z',html_url:`${repo}/releases/tag/${tag}`,body:'Fixture release notes',assets:[{name:filename,size:bytes.length,digest:`sha256:${digest}`,browser_download_url:`${repo}/releases/download/${tag}/${filename}`}]};
const browser = await chromium.launch({executablePath:process.env.STUDIO_BROWSER || undefined,headless:true,chromiumSandbox:true,args:['--disable-background-networking','--disable-component-update']});
try {
  for (const viewport of [{width:1280,height:800},{width:390,height:844}]) {
    const context = await browser.newContext({viewport,offline:true,serviceWorkers:'block'});
    const page = await context.newPage(), errors = [], unexpected = [], commands = [];
    let available = false, state = 'STARTED', operation = oldId, failNetwork = false, remoteCalls = 0, archived = false, resolved = false;
    let admissionReady=false,corruptLog=false,preIntentReject=false,rejectedAttempt=null,proofWriteBusy=true;
    let localView='healthy',legacyUnavailable=false;
    page.setDefaultTimeout(10000);
    page.on('pageerror',error=>errors.push(error.message));
    await context.exposeFunction('testNative',async(command,args)=>{
      commands.push({command,args});
      if(command==='local_dev_status') {
        assert.equal(args,undefined);
        if(localView==='unavailable')throw Error('Local status reader unavailable');
        return {schema:'OpenRemaster.LocalStudioStatus.v1',captured_epoch:Date.now()/1000-(localView==='stale'?20:0),
          mode:'LOCAL_DEV',source:'LOCAL_NATIVE_READONLY',read_only:true,azure_required:false,witness_required:false,production_go:false,
          host:{state:'IDLE',healthy:true,process_alive:true,heartbeat_age_seconds:1,generation:'d'.repeat(32)},
          counts:{queued:0,running:0,committed:1,hold:0,checkpoint_pending:1},
          jobs:[{operation_id:'e'.repeat(32),scenario:'build_studio_dev',state:'COMMITTED',launch_count:1,project:'studio',
            knowledge:{state:'CHECKPOINT_PENDING',project:'OpenRemasterStudio',attempts:1,reason:'Fixture metadata hook unavailable'}}]};
      }
      if(command==='studio_capabilities') return {schema:'OpenRemaster.StudioCapabilities.v1',worker_compiled:available,worker_ready:available&&!legacyUnavailable,control_ready:available&&!legacyUnavailable,recovery_supported:available&&!legacyUnavailable,log_archive_supported:available&&!legacyUnavailable,worker_scope:available?scope:null,reason:available?(legacyUnavailable?'Legacy fixture worker unavailable':'Pinned DEV broker available'):portableReason,production_go:false,
        preflight:{schema:'OpenRemaster.DevPreflight.v1',scope:available?scope:null,checked_at_ms:Date.now(),valid_for_ms:30000,can_submit:available&&admissionReady&&!legacyUnavailable,production_go:false,
          checks:['native','worker','owner','resources','game','account','source'].map(id=>({id,status:available&&(admissionReady||['native','worker'].includes(id))?'PASS':'UNKNOWN',detail:'Mocked IPC diagnostic fixture',next_step:'Verify original admission'}))}};
      if(command==='studio_open_release') return;
      assert.equal(command,'dev_worker_call');
      const request=args.request;
      assert.equal(request.scenario,'build_studio_dev');
      const metadata=()=>({schema:'OpenRemaster.DevWorkflowResult.v2',control_scope:scope,control_verified:true,dev_receipt_verified:false,evidence_sha256:digest,recovery:{allowed:state==='HOLD'||!!rejectedAttempt,reason:'Terminal fixture confirms the owned build stopped.'},
        ...(rejectedAttempt?{launch_count:0,ack:null,commit:null,worker:undefined,not_admitted:{schema:'OpenRemaster.NotAdmitted.v1',operation_id:operation,scope,attempt_id:rejectedAttempt,reason:'Fixture rejected before intent',record_sha256:'e'.repeat(64),production_go:false}}:{}),
        archive:archived?{path:'C:/DEV/archives/'+operation,operation_id:operation,evidence_sha256:digest,manifest_sha256:'f'.repeat(64),log_count:2,retention:'KEEP_UNTIL_EXPLICIT_EXPORT_AND_REVIEW'}:null,resolution:resolved?{disposition:'ACKNOWLEDGED_NO_RETRY',operation_id:operation,scope,evidence_sha256:digest,archive_manifest_sha256:'f'.repeat(64),record_sha256:'e'.repeat(64),reason:'Reviewed stopped fixture; preserve evidence.',new_operation_allowed:true,production_go:false}:null});
      if(request.action==='logs') {
        assert.equal(request.operation_id,operation);assert.equal(request.recovery.expected_evidence_sha256,digest);
        const spec=request.log,data=spec.source==='bundle'?zipBytes:logBytes,part=data.subarray(spec.offset,spec.offset+spec.limit);
        return JSON.stringify({schema:'OpenRemaster.DevLogPage.v1',operation_id:operation,scope,evidence_sha256:digest,source:spec.source,name:spec.name,offset:spec.offset,next_offset:spec.offset+part.length,total_bytes:data.length,
          bytes_base64:part.toString('base64'),chunk_sha256:corruptLog?'0'.repeat(64):createHash('sha256').update(part).digest('hex'),file_sha256:spec.source==='live'?null:spec.source==='bundle'?zipSha:logSha,
          manifest_sha256:spec.source==='live'?null:'f'.repeat(64),verified:spec.source!=='live',eof:spec.offset+part.length===data.length,production_go:false});
      }
      if(request.action==='export') return JSON.stringify({schema:'OpenRemaster.DevLogExport.v1',operation_id:operation,scope,evidence_sha256:digest,manifest_sha256:'f'.repeat(64),bytes:zipBytes.length,sha256:zipSha,production_go:false});
      if(request.action==='submit') {
        operation=request.operation_id;archived=false;resolved=false;
        const saved=await page.evaluate(key=>JSON.parse(localStorage.getItem(key)),`orf-studio-operation-v2-${scope}`);
        assert.equal(saved.operation,operation);
        assert.equal(saved.attempt_id,request.attempt_id);
        if(preIntentReject){
          if(proofWriteBusy){state='NOT_FOUND';rejectedAttempt=null;throw Error('Fixture proof writer busy');}
          state='DENIED';rejectedAttempt=request.attempt_id;return JSON.stringify({state,operation_id:operation,production_go:false,independent_authority:false,engine:'unsigned-studio-dev-build',...metadata()});
        }
        return JSON.stringify({schema:'OpenRemaster.DevWorkflowResult.v1',state:'REQUESTED',operation_id:operation,production_go:false,independent_authority:false,engine:'unsigned-studio-dev-build',dev_receipt_verified:true,automatic_retry:false});
      }
      assert.ok(['status','archive','resolve','prove_not_admitted'].includes(request.action));assert.equal(request.operation_id,operation);
      if(request.action!=='status')assert.equal(request.recovery.expected_evidence_sha256,digest);
      if(['archive','resolve'].includes(request.action))archived=true;
      if(request.action==='prove_not_admitted'){assert.equal(request.attempt_id,(await page.evaluate(key=>JSON.parse(localStorage.getItem(key)),`orf-studio-operation-v2-${scope}`)).attempt_id);state='DENIED';rejectedAttempt=request.attempt_id;}
      if(request.action==='resolve') {assert.equal(request.recovery.acknowledge,true);assert.ok(request.recovery.reason.length>=10);if(rejectedAttempt)assert.equal(request.attempt_id,rejectedAttempt);resolved=true;}
      return JSON.stringify({schema:'OpenRemaster.DevWorkflowResult.v1',state,operation_id:operation,production_go:false,independent_authority:false,engine:'unsigned-studio-dev-build',dev_receipt_verified:true,automatic_retry:false,launch_count:['BUSY','DENIED'].includes(state)?undefined:1,reason:state==='HOLD'?'Fixture failure needs review':undefined,ack:{operation_id:operation},commit:state==='COMMITTED'?{operation_id:operation}:null,worker:state==='COMMITTED'?{success:true,owned_tree_stopped:true,wrapper_exit:0,artifacts:{studio_exe:'C:/DEV/Studio.exe',studio_exe_sha256:digest}}:undefined,logs:{'stdout.log':'Compiling Studio fixture','stderr.log':''},...metadata()});
    });
    await context.addInitScript(()=>{window.__TAURI_INTERNALS__={invoke:(command,args)=>window.testNative(command,args)};});
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
      await page.locator('main#openremaster-studio-ready-v1').waitFor();
      assert.equal(await page.title(),'OpenRemaster Studio workspace');
      const local=page.getByRole('region',{name:'Local DEV status'});
      await local.getByText('Host: IDLE · healthy',{exact:true}).waitFor();
      await local.getByText('Committed · launches 1',{exact:true}).waitFor();
      await local.getByText('Fixture metadata hook unavailable',{exact:true}).waitFor();
      await local.screenshot({path:resolve(screenshots,`local-status-${viewport.width}.png`)});
      localView='stale';await local.getByRole('button',{name:'Refresh local status',exact:true}).click();
      await local.getByText(/Local DEV snapshot expired/).waitFor();
      assert.equal(await local.getByRole('table').count(),0);
      localView='unavailable';await local.getByRole('button',{name:'Refresh local status',exact:true}).click();
      await local.getByText(/Local status reader unavailable/).waitFor();
      assert.equal(await local.getByRole('table').count(),0);
      localView='healthy';await local.getByRole('button',{name:'Refresh local status',exact:true}).click();
      await local.getByText('Host: IDLE · healthy',{exact:true}).waitFor();
      const worker=page.getByRole('region',{name:'Studio DEV operation'});
      await worker.getByText(portableReason,{exact:true}).waitFor();
      await page.keyboard.press('Control+k');
      const search=page.getByRole('combobox',{name:'Find a Studio page'});
      assert.equal(await search.evaluate(el=>el===document.activeElement),true);
      await search.fill('Build');await search.press('ArrowDown');await search.press('ArrowUp');await search.press('Escape');
      assert.equal(await search.inputValue(),'');
      await search.press('Tab');assert.equal(await search.evaluate(el=>el===document.activeElement),false);
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
      assert.ok(await releases.evaluate(el=>el.scrollWidth<=el.clientWidth),'Release details must fit the viewport');
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
      state='QUEUED';
      await worker.getByRole('button',{name:'Refresh build status'}).click();
      await worker.getByText('Queued by HomePC worker',{exact:true}).waitFor();
      state='RUNNING';
      await worker.getByRole('button',{name:'Refresh build status'}).click();
      await worker.getByText('Building on HomePC',{exact:true}).waitFor();
      state='BUSY';
      await worker.getByRole('button',{name:'Refresh build status'}).click();
      await worker.getByText('Worker busy',{exact:true}).waitFor();
      assert.equal(await worker.getByTestId('dev-run').isDisabled(),true);
      state='DENIED';
      await worker.getByRole('button',{name:'Refresh build status'}).click();
      await worker.getByText('Request denied',{exact:true}).waitFor();
      assert.equal(await worker.getByTestId('dev-run').isDisabled(),true);
      state='COMMITTED';
      await worker.getByRole('button',{name:'Refresh build status'}).click();
      await worker.getByText('Build complete',{exact:true}).waitFor();
      await worker.getByText('C:/DEV/Studio.exe',{exact:true}).waitFor();
      assert.equal(await worker.getByTestId('dev-run').isDisabled(),true);
      await worker.getByText('Owner / writer lease · UNKNOWN',{exact:true}).waitFor();
      admissionReady=true;
      await worker.getByRole('button',{name:'Refresh diagnostics'}).click();
      await worker.getByText('All required DEV checks passed.',{exact:true}).waitFor();
      await worker.getByRole('button',{name:'Archive build logs'}).click();
      await worker.getByText('C:/DEV/archives/'+operation,{exact:true}).waitFor();
      const viewer=worker.getByRole('region',{name:'DEV log viewer'});
      await viewer.getByLabel('Log source').selectOption('archive');
      await viewer.getByRole('button',{name:'Load log',exact:true}).click();
      await viewer.getByText('Full archived file verified',{exact:false}).waitFor();
      await viewer.getByLabel('Search this page').fill('retained');
      await viewer.getByLabel('Log level').selectOption('error');
      assert.match(await viewer.locator('pre').innerText(),/error: retained fixture error/);
      assert.doesNotMatch(await viewer.locator('pre').innerText(),/Compiling/);
      await viewer.getByRole('button',{name:'Next page'}).click();
      await viewer.getByText('Bytes 65536–131072',{exact:false}).waitFor();
      corruptLog=true;
      await viewer.getByRole('button',{name:'Load log',exact:true}).click();
      await viewer.getByText('Error: Log page checksum mismatch',{exact:true}).waitFor();
      await worker.getByText('Build complete',{exact:true}).waitFor();corruptLog=false;
      const downloadPromise=page.waitForEvent('download');
      await viewer.getByRole('button',{name:'Export complete diagnostic ZIP'}).click();
      const download=await downloadPromise,path=resolve(screenshots,`diagnostics-${viewport.width}.zip`);
      await download.saveAs(path);assert.deepEqual(readFileSync(path),zipBytes);
      await viewer.getByText('Complete diagnostic ZIP verified',{exact:false}).waitFor();
      await viewer.getByLabel('Log source').selectOption('live');
      await viewer.getByRole('button',{name:'Load log',exact:true}).click();
      await viewer.getByText('Live output · full-file verification pending',{exact:false}).waitFor();
      await viewer.getByRole('checkbox',{name:'Follow live output every 10 seconds'}).check();
      assert.equal(commands.filter(call=>call.args?.request?.action==='submit').length,0);
      const peer=await context.newPage();
      await peer.goto(origin+'/#buildlab');
      const peerWorker=peer.getByRole('region',{name:'Studio DEV operation'});
      await peerWorker.getByText('Build complete',{exact:true}).waitFor();
      const attempts=await Promise.allSettled([
        worker.getByRole('button',{name:'Build a DEV candidate'}).click({timeout:1500}),
        peerWorker.getByRole('button',{name:'Build a DEV candidate'}).click({timeout:1500}),
      ]);
      assert.ok(attempts.some(attempt=>attempt.status==='fulfilled'));
      await page.waitForFunction(key=>JSON.parse(localStorage.getItem(key))?.result?.state==='REQUESTED',`orf-studio-operation-v2-${scope}`);
      assert.equal(commands.filter(call=>call.args?.request?.action==='submit').length,1);
      await peer.close();
      await worker.getByText(operation,{exact:true}).waitFor();
      assert.notEqual(operation,oldId);
      assert.equal(await worker.getByTestId('dev-run').isDisabled(),true);
      await page.reload();
      await worker.getByText('Build complete',{exact:true}).waitFor();
      assert.equal(commands.filter(call=>call.args?.request?.action==='submit').length,1);
      state='HOLD';
      await worker.getByRole('button',{name:'Refresh build status'}).click();
      await worker.getByText('Held for review',{exact:true}).waitFor();
      await worker.getByText('Reason: Fixture failure needs review',{exact:true}).waitFor();
      assert.ok(await worker.evaluate(el=>el.scrollWidth<=el.clientWidth),'Operation details must fit the viewport');
      assert.equal(await worker.getByTestId('dev-run').isDisabled(),true);
      const resolveHold=worker.getByRole('button',{name:'Archive evidence and acknowledge hold'});
      assert.equal(await resolveHold.isDisabled(),true);
      await worker.getByLabel('Resolution note').fill('Reviewed stopped fixture; preserve evidence.');
      await worker.getByRole('checkbox',{name:'I acknowledge this hold.',exact:false}).check();
      await resolveHold.click();
      await worker.getByText('Hold acknowledged.',{exact:false}).waitFor();
      await worker.getByRole('button',{name:'Refresh diagnostics'}).click();
      await page.waitForFunction(()=>document.querySelector('[data-testid="dev-run"]')?.disabled===false);
      assert.equal(await worker.getByTestId('dev-run').isEnabled(),true);
      assert.equal(commands.filter(call=>call.args?.request?.action==='submit').length,1);
      preIntentReject=true;
      await worker.getByRole('button',{name:'Build a DEV candidate'}).click();
      await worker.getByText('Error: Fixture proof writer busy',{exact:false}).waitFor();
      await worker.getByRole('button',{name:'Refresh build status'}).click();
      const verifyAttempt=worker.getByRole('button',{name:'Verify this attempt was not admitted'});
      await verifyAttempt.waitFor();
      proofWriteBusy=false;
      await verifyAttempt.click();
      await worker.getByText('The proof matches this saved attempt.',{exact:false}).waitFor();
      assert.equal(await worker.getByTestId('dev-run').isDisabled(),true);
      await page.reload();
      await worker.getByText('The proof matches this saved attempt.',{exact:false}).waitFor();
      await worker.getByLabel('Resolution note').fill('Reviewed the fresh pre-intent rejection.');
      await worker.getByRole('checkbox',{name:'I acknowledge this hold.',exact:false}).check();
      await worker.getByRole('button',{name:'Archive evidence and acknowledge hold'}).click();
      await worker.getByText('Hold acknowledged.',{exact:false}).waitFor();
      await page.waitForFunction(()=>document.querySelector('[data-testid="dev-run"]')?.disabled===false);
      assert.equal(await worker.getByTestId('dev-run').isEnabled(),true);
      await page.evaluate(key=>{const saved=JSON.parse(localStorage.getItem(key));delete saved.attempt_id;localStorage.setItem(key,JSON.stringify(saved));},`orf-studio-operation-v2-${scope}`);
      await page.reload();
      await worker.getByText('The proof does not match a fresh saved attempt',{exact:false}).waitFor();
      assert.equal(await worker.getByTestId('dev-run').isDisabled(),true);
      assert.equal(commands.filter(call=>call.args?.request?.action==='submit').length,2);
      assert.equal(commands.filter(call=>call.args?.request?.action==='prove_not_admitted').length,1);
      await page.reload();
      await worker.getByText('Hold acknowledged.',{exact:false}).waitFor();
      assert.equal(commands.filter(call=>call.args?.request?.action==='resolve').length,2);
      assert.equal(commands.filter(call=>call.args?.request?.action==='submit').length,2);
      assert.ok(await worker.evaluate(el=>el.scrollWidth<=el.clientWidth),'Resolved hold must fit the viewport');
      legacyUnavailable=true;await page.reload();
      await worker.getByText('Saved observation only. The legacy worker is unavailable; this record is not current admission or artifact verification.',{exact:true}).waitFor();
      assert.equal(await worker.getByTestId('dev-run').isEnabled(),false);
      legacyUnavailable=false;await page.reload();
      await worker.getByText(/Hold acknowledged\. Evidence is retained/).waitFor();
      await worker.screenshot({path:resolve(screenshots,`worker-${viewport.width}.png`)});
      await page.screenshot({path:resolve(screenshots,`operation-${viewport.width}.png`),fullPage:true});
      assert.deepEqual(unexpected,[]);assert.deepEqual(errors,[]);
      console.log(`PASS ${viewport.width}x${viewport.height}: workspace readiness, read-only local status/checkpoint separation, stale/error clearing, capabilities, release/CI identity, local file checksums, offline clearing, durable restore, rejected status hold and two-window single submit, log archival and explicit hold resolution`);
    } catch (error) {
      console.error('Studio GUI failure', {errors, unexpected, remoteCalls});
      console.error(await page.locator('main').innerText().catch(()=>page.locator('body').innerText()));
      await page.screenshot({path:resolve(screenshots,`failure-${viewport.width}.png`),fullPage:true});
      throw error;
    } finally {await context.close();}
  }
} finally {await browser.close();}
