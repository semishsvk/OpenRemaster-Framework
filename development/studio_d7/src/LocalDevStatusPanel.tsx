import {useEffect,useRef,useState} from 'react';
import {localSnapshotFresh,parseLocalDevStatus,type LocalDevSnapshot,type LocalDevJob} from './local-dev-status';

const buildLabels:Record<string,string>={QUEUED:'Queued',STARTED:'Running',COMMITTED:'Committed',HOLD:'Hold - unresolved',UNKNOWN:'Unknown - reconciliation required',FAILED_SETTLED:'Failed - settled'};
const knowledgeLabels:Record<string,string>={NOT_REQUESTED:'Not requested',PENDING:'Pending',RUNNING:'Saving',VERIFIED:'Verified',CHECKPOINT_PENDING:'Checkpoint pending'};

export function LocalDevCounts({snapshot}:{snapshot:LocalDevSnapshot}){
  return <p>Queued: {snapshot.counts.queued} · Running: {snapshot.counts.running} · Committed: {snapshot.counts.committed} · {snapshot.schema==='OpenRemaster.LocalStudioStatus.v2'?'Unresolved holds':'Raw holds (v1)'}: {snapshot.counts.hold} · Settled failures: {snapshot.schema==='OpenRemaster.LocalStudioStatus.v2'?snapshot.counts.failed_settled:'Unavailable in v1'} · Checkpoints pending: {snapshot.counts.checkpoint_pending}</p>;
}

export function LocalDevJobRow({job}:{job:LocalDevJob}){
  return <tr>
    <td>{job.project}<br/><code>{job.operation_id}</code></td>
    <td>{buildLabels[job.state]} · launches {job.launch_count}
      {job.original_state&&<p>Original state: <code>{job.original_state}</code> · effective state: <code>{job.state}</code></p>}
      {job.disposition&&<p>Disposition: <code>{job.disposition.kind}</code><br/>Receipt SHA-256: <code>{job.disposition.receipt_sha256}</code><br/>Reported by the pinned read-only provider; no retry or success implied.</p>}
    </td>
    <td>{knowledgeLabels[job.knowledge.state]}{job.knowledge.reason&&<p>{job.knowledge.reason}</p>}</td>
  </tr>;
}

export default function LocalDevStatusPanel(){
  const [snapshot,setSnapshot]=useState<LocalDevSnapshot|null>(null);
  const [error,setError]=useState('');
  const [clock,setClock]=useState(Date.now());
  const [busy,setBusy]=useState(false);
  const refresh=useRef<()=>void>(()=>{});
  useEffect(()=>{
    let mounted=true,pending=false,lastCapture=0;
    const read=async()=>{
      if(pending)return;
      pending=true;setBusy(true);
      try{
        const invoke=window.__TAURI_INTERNALS__?.invoke;
        if(!invoke)throw Error('Open the native HomePC Studio to read local worker status.');
        const value=parseLocalDevStatus(await invoke('local_dev_status'));
        if(value.captured_epoch<lastCapture)throw Error('An older local snapshot was rejected.');
        lastCapture=value.captured_epoch;
        if(mounted){setSnapshot(value);setClock(Date.now());setError('');}
      }catch(reason){if(mounted){setSnapshot(null);setError(String(reason).slice(0,350));}}
      finally{pending=false;if(mounted)setBusy(false);}
    };
    refresh.current=()=>void read();void read();
    const poll=setInterval(()=>void read(),5000),expiry=setInterval(()=>setClock(Date.now()),1000);
    return()=>{mounted=false;clearInterval(poll);clearInterval(expiry);refresh.current=()=>{};};
  },[]);
  const fresh=snapshot&&localSnapshotFresh(snapshot,clock);
  const host=fresh?snapshot.host:null;
  return <section className="panel" aria-label="Local DEV status" style={{padding:24,marginBottom:24,overflowWrap:'anywhere'}}>
    <div className="eyebrow">LOCAL DEV · READ ONLY</div><h2>Local worker</h2>
    <p>Local operator workflow. Azure and an external Witness are not required for local development.</p>
    <p role="status">{host?`Host: ${host.state} · ${host.healthy?'healthy':'unavailable'}`:snapshot?'Local status expired. Refresh to read the current worker.':error||'Reading local worker status…'}</p>
    <button disabled={busy} onClick={()=>refresh.current()}>Refresh local status</button>
    {fresh&&<>
      <p>Captured: <time dateTime={new Date(snapshot.captured_epoch*1000).toISOString()}>{new Date(snapshot.captured_epoch*1000).toLocaleString('en-GB')}</time> · refreshes every 5 seconds</p>
      <p>{snapshot.schema==='OpenRemaster.LocalStudioStatus.v2'?'Status v2: disposition-aware history.':'Status v1: raw history; settlement evidence is unavailable.'}</p>
      <LocalDevCounts snapshot={snapshot}/>
      {snapshot.jobs.length===0?<p>No local job history is available.</p>:<div style={{overflowX:'auto'}}><table>
        <caption>Recent local jobs</caption><thead><tr><th>Project / operation</th><th>Build result</th><th>Knowledge checkpoint</th></tr></thead>
        <tbody>{snapshot.jobs.map(job=><LocalDevJobRow key={job.operation_id} job={job}/>)}</tbody></table></div>}
    </>}
    <small>A committed build and its knowledge checkpoint are separate results. This view cannot start, retry or authorize a job. Historical production evidence does not determine local build readiness.</small>
  </section>;
}
