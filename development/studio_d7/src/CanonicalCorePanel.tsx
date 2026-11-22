import {useState} from 'react';
import {readStoredResponse} from './stored-json';
const REV='8195f3754219b487deb0947a29d8af6cfe1babc9',PINS='e69bb6ced690b239ab43fc2a8ec3e4ed868128677f8198f3c6af938514164ba0';
const hex=(v:unknown)=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
type Flat=Record<string,unknown>;
function object(v:unknown):Flat{if(v===null||typeof v!=='object'||Array.isArray(v))throw Error('OBJECT');return v as Flat;}
function safety(v:Flat){for(const k of ['may_dispatch','production_authority','automatic_retry'])if(v[k]!==false)throw Error('AUTHORITY');}
function context(v:unknown):Flat{
 const c=object(v);safety(c);
 if(Object.keys(c).sort().join()!=='schema core_revision core_pins_sha256 release_sha256 commit_id candidate_sha256 may_dispatch production_authority automatic_retry'.split(' ').sort().join()||c.schema!=='ORF.CanonicalCore.Context.v1'||c.core_revision!==REV||c.core_pins_sha256!==PINS||!hex(c.release_sha256)||!hex(c.commit_id)||!hex(c.candidate_sha256))throw Error('CONTEXT');
 return c;
}
function result(v:unknown,c:Flat,id:string):Flat{
 const r=object(v);safety(r);
 const keys='schema status request_id release_sha256 commit_id core_revision core_pins_sha256 candidate_sha256 core_report_sha256 evidence_id model_job_id project core_module clock_mode native_boundary may_dispatch may_spawn_native production_authority automatic_retry worker_started';
 if(Object.keys(r).sort().join()!==keys.split(' ').sort().join()||r.schema!=='ORF.CanonicalCore.Result.v1'||r.status!=='CANONICAL_CORE_TEST_VALIDATED_NATIVE_MODEL_HOLD'||r.request_id!==id||r.core_module!=='openremaster.evidence_report'||r.clock_mode!=='CONTROLLED_SYNTHETIC_TICK_50'||r.native_boundary!=='EXISTING_NATIVE_V2_MODEL_CREATED_HOLD'||r.model_job_id!=='test_'+String(c.commit_id)||!hex(r.core_report_sha256)||!hex(r.evidence_id)||typeof r.project!=='string'||!/^[\x20-\x7e]{1,128}$/.test(r.project)||r.worker_started!==false||r.may_spawn_native!==false)throw Error('RESULT');
 for(const k of ['release_sha256','commit_id','core_revision','core_pins_sha256','candidate_sha256'])if(r[k]!==c[k])throw Error('BINDING');return r;
}
export default function CanonicalCorePanel(){
 const [value,setValue]=useState<Flat|null>(null),[busy,setBusy]=useState(false),[status,setStatus]=useState('NO CANONICAL OBSERVATION');
 async function load(){
  setValue(null);setBusy(true);setStatus('LOADING');const abort=new AbortController(),timer=setTimeout(()=>abort.abort(),5000);
  const id=Array.from(crypto.getRandomValues(new Uint8Array(32)),n=>n.toString(16).padStart(2,'0')).join('');
  try{
   const options={cache:'no-store' as RequestCache,signal:abort.signal,redirect:'error' as RequestRedirect};
   const c=context(await readStoredResponse(await fetch('/api/canonical-core/context',options),16384,abort.signal));
   const r=result(await readStoredResponse(await fetch('/api/canonical-core/review',{...options,headers:{'X-ORF-Request':id,'X-ORF-Release':String(c.release_sha256)}}),16384,abort.signal),c,id);
   abort.signal.throwIfAborted();setValue(r);setStatus('CANONICAL CORE TEST / NATIVE MODEL HOLD');
  }catch{setValue(null);setStatus('HOLD / REJECTED');}finally{clearTimeout(timer);setBusy(false);}
 }
 return <section className="panel" data-testid="canonical-core-panel"><div className="eyebrow">CANONICAL CORE / ISOLATED TEST</div><h2>Canonical Core TEST review</h2><p>Real pinned evidence library · local TEST signatures and controlled time · Native v2 MODEL. No worker or production authority.</p><button disabled={busy} onClick={load}>Review canonical TEST result</button><p role="status">{status}</p>{value&&<div data-testid="canonical-core-result"><p>{String(value.project)}</p><p>Core revision: {String(value.core_revision)}</p><p>Request: {String(value.request_id)}</p><p>Release: {String(value.release_sha256)}</p><p>Core report: {String(value.core_report_sha256)}</p><p>Native: CREATED / HOLD · worker started: false</p><p>HOLD_NO_AUTO_RETRY · Production NO-GO</p></div>}</section>;
}
