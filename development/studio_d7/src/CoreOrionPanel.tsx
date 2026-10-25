import { useState } from 'react';
import {readReceipt,type Receipt} from './core-orion-receipt';
export default function CoreOrionPanel(){
 const [value,setValue]=useState<Receipt|null>(null),[busy,setBusy]=useState(false),[status,setStatus]=useState('NO OBSERVATION');
 async function load(){
  setValue(null);setBusy(true);setStatus('LOADING');const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),5000);
  try{
   const response=await fetch('/core-orion-observation.json',{cache:'no-store',redirect:'error',signal:controller.signal});
   const v=await readReceipt(response);
   setValue(v);setStatus('VERIFIED TEST RECEIPT / HOLD');
  }catch{setValue(null);setStatus('HOLD / REJECTED');}finally{clearTimeout(timer);setBusy(false);}
 }
 return <section className="panel" data-testid="core-orion-panel"><div className="eyebrow">CORE EXTENSION / ORION</div><h2>Offline receipt review</h2><p>Uložený výsledok Core rozšírenia a existujúceho ORION verifiera. Tri testovacie podpisy, syntetické dáta a testovací čas. Neoveruje produkčnú identitu ani aktuálny stav Core.</p><button className="top-button" disabled={busy} onClick={load}>Load Core receipt</button><p role="status">{status}</p>{value && <div data-testid="core-orion-result"><p>Signatures: {value.signatureCount}</p><p>{value.project} / {value.runId}</p><code>{value.fixtureSha256}</code><p>HOLD_NO_AUTO_RETRY · Production NO-GO</p></div>}</section>;
}
