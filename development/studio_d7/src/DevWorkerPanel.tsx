import {useState} from "react";
type DevResult={state:string;operation_id?:string;launch_count?:number;ack?:unknown;commit?:unknown;reason?:string;production_go:false;dev_receipt_verified?:boolean;worker?:{artifacts?:{studio_exe:string;studio_exe_sha256:string;signature_status:string}}};
declare global {interface Window {__TAURI_INTERNALS__?:{invoke:(command:string,args:unknown)=>Promise<string>}}}
export default function DevWorkerPanel(){
 const [operation,setOperation]=useState(()=>localStorage.getItem("orf-unified-dev-build-operation")||"");
 const [result,setResult]=useState<DevResult|null>(null);const [error,setError]=useState("");const [busy,setBusy]=useState(false);
 const native=!!window.__TAURI_INTERNALS__?.invoke;
 async function call(action:"submit"|"status"){
  if(busy)return;setBusy(true);setError("");
  const id=action==="submit"?crypto.randomUUID().replaceAll("-",""):operation;
  if(action==="submit"){setOperation(id);localStorage.setItem("orf-unified-dev-build-operation",id);}
  try{
   if(!window.__TAURI_INTERNALS__)throw Error("Open an unsigned Studio DEV build with native IPC.");
   const raw=await window.__TAURI_INTERNALS__.invoke("dev_worker_call",{request:{action,operation_id:id,scenario:"build_studio_dev"}});
   const value=JSON.parse(raw) as DevResult;if(value.production_go!==false||typeof value.state!=="string")throw Error("Invalid DEV response");setResult(value);
  }catch(e){setError(String(e));}finally{setBusy(false);}
 }
 return <section className="panel" data-testid="dev-worker-panel" style={{padding:24,marginBottom:24}}>
  <div className="eyebrow">DEV UNSIGNED</div><h2>Zostavenie Studio DEV</h2>
  <p>The native worker builds the frontend and Studio executable from pinned D7 sources for unsigned development use.</p>
  <p>Native IPC: <strong>{native?"connected":"unavailable"}</strong></p>
  <div style={{display:"flex",gap:12,flexWrap:"wrap"}}>
   <button data-testid="dev-run" disabled={busy||!native} onClick={()=>void call("submit")}>Build a DEV candidate</button>
   <button data-testid="dev-status" disabled={busy||!native||!operation} onClick={()=>void call("status")}>Refresh build status</button>
  </div>
  <p>Operation: <code>{operation||"none"}</code></p>
  <div role="status" aria-live="polite">{busy?"Loading":result?.state||"Ready"}</div>
  {error&&<p role="alert">{error}</p>}
  {result&&<><p>Launches: {result.launch_count??0} · ACK: {result.ack?"recorded":"pending"} · Commit: {result.commit?"recorded":"pending"}</p>
  <pre style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere",maxHeight:420,overflow:"auto"}}>{JSON.stringify(result,null,2)}</pre></>}
  <small>Unknown outcomes remain on hold. The worker never automatically repeats the same build operation.</small>
 </section>;
}
