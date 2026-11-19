import {useEffect, useRef, useState} from 'react';
import {bytesDigest, filterLog, parseLogExport, parseLogPage, type LogPage, type LogSource} from './dev-diagnostics';
import type {DevResult} from './dev-worker';

export default function DevLogViewer({result,scope,connected}:{result:DevResult;scope:string;connected:boolean}) {
  const [source,setSource]=useState<'live'|'archive'>('live'),[name,setName]=useState('stdout.log');
  const [page,setPage]=useState<LogPage|null>(null),[query,setQuery]=useState(''),[level,setLevel]=useState('all');
  const [error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false),[follow,setFollow]=useState(false);
  const serial=useRef(0),running=useRef(false);
  const op=result.operation_id, evidence=result.evidence_sha256;
  useEffect(()=>{serial.current++;setPage(null);setError('');setNotice('');setFollow(false);return()=>{serial.current++;};},[op,evidence,source,name]);

  async function invoke(action:string,extra:Record<string,unknown>={}) {
    const call=window.__TAURI_INTERNALS__?.invoke;
    if(!call||!evidence)throw Error('Native log connection unavailable');
    return call('dev_worker_call',{request:{action,operation_id:op,scenario:'build_studio_dev',recovery:{expected_evidence_sha256:evidence},...extra}});
  }
  async function fetchPage(kind:LogSource,file:string,offset:number,limit:number,manifest?:string) {
    return parseLogPage(await invoke('logs',{log:{source:kind,name:file,offset,limit,...(manifest?{manifest_sha256:manifest}:{})}}),op,scope,evidence!,kind,file,offset,manifest);
  }
  async function read(offset=0) {
    if(running.current||!connected||!evidence)return;
    running.current=true;setBusy(true);setError('');setNotice('');const token=serial.current;
    try {
      const value=await fetchPage(source,name,offset,65536,result.archive?.manifest_sha256);
      if(token===serial.current)setPage(value);
    } catch(reason){if(token===serial.current){setError(String(reason));setPage(null);}}
    finally{running.current=false;setBusy(false);}
  }
  useEffect(()=>{
    if(!follow||source!=='live')return;
    const timer=setInterval(()=>void read(Math.max(0,(page?.total_bytes??65536)-65536)),10000);
    return()=>clearInterval(timer);
  },[follow,source,name,op,evidence,page?.total_bytes]);

  async function exportBundle() {
    if(running.current||!evidence)return;
    running.current=true;setBusy(true);setError('');setNotice('');const token=serial.current;
    try {
      const bundle=parseLogExport(await invoke('export'),op,scope,evidence);
      const chunks:Uint8Array[]=[];let offset=0;
      while(offset<bundle.bytes) {
        const part=await fetchPage('bundle','diagnostics.zip',offset,1024*1024,bundle.manifest_sha256);
        if(token!==serial.current)return;
        if(part.total_bytes!==bundle.bytes||part.file_sha256!==bundle.sha256)throw Error('Export changed while downloading');
        chunks.push(part.bytes);offset=part.next_offset;
      }
      const bytes=new Uint8Array(bundle.bytes);let at=0;
      for(const chunk of chunks){bytes.set(chunk,at);at+=chunk.length;}
      if(await bytesDigest(bytes)!==bundle.sha256)throw Error('Diagnostic ZIP checksum mismatch');
      if(token!==serial.current)return;
      const url=URL.createObjectURL(new Blob([bytes.buffer],{type:'application/zip'}));
      const link=document.createElement('a');link.href=url;link.download=`Studio-DEV-${op}-diagnostics.zip`;link.click();
      setTimeout(()=>URL.revokeObjectURL(url),30000);
      setNotice(`Complete diagnostic ZIP verified · SHA-256 ${bundle.sha256}`);
    }catch(reason){if(token===serial.current)setError(String(reason));}
    finally{running.current=false;setBusy(false);}
  }
  const text=page?new TextDecoder().decode(page.bytes):'';
  return <section aria-label="DEV log viewer" style={{marginTop:24}}>
    <h3>Build logs</h3>
    <p>Read complete logs by page. Live output can change; archived files are checked against their manifest. Search and filters apply to the displayed page.</p>
    <div style={{display:'flex',gap:12,flexWrap:'wrap'}}>
      <label>Log source <select value={source} disabled={busy} onChange={event=>setSource(event.target.value as 'live'|'archive')}><option value="live">Live output</option><option value="archive" disabled={!result.archive}>Verified archive</option></select></label>
      <label>Log file <select value={name} disabled={busy} onChange={event=>setName(event.target.value)}><option>stdout.log</option><option>stderr.log</option></select></label>
      <button disabled={busy||!connected} onClick={()=>void read()}>Load log</button>
      <button disabled={busy||!page||page.offset===0} onClick={()=>void read(Math.max(0,(page?.offset??0)-65536))}>Previous page</button>
      <button disabled={busy||!page||page.eof} onClick={()=>void read(page!.next_offset)}>Next page</button>
    </div>
    <p><label>Search this page <input value={query} maxLength={256} onChange={event=>setQuery(event.target.value)} /></label>{' '}
      <label>Log level <select value={level} onChange={event=>setLevel(event.target.value)}><option value="all">All lines</option><option value="error">Errors</option><option value="warning">Warnings</option></select></label></p>
    <label><input type="checkbox" checked={follow} disabled={source!=='live'} onChange={event=>setFollow(event.target.checked)} />Follow live output every 10 seconds</label>
    {page&&<><p role="status">Bytes {page.offset}–{page.next_offset} of {page.total_bytes} · {page.verified?'Full archived file verified':'Live output · full-file verification pending'}{page.eof?' · end of file':''}</p>
      <pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere',maxHeight:360,overflow:'auto'}}>{filterLog(text,query,level)||'No matching output on this page.'}</pre></>}
    {['COMMITTED','HOLD','DENIED','NOT_FOUND'].includes(result.state)&&<p><button disabled={busy||!connected||!evidence} onClick={()=>void exportBundle()}>Export complete diagnostic ZIP</button></p>}
    {busy&&<p role="status">Reading and verifying logs…</p>}{error&&<p role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}
  </section>;
}
