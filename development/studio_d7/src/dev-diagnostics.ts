export const diagnosticIds = ['native','worker','owner','resources','game','account','source'] as const;
export const diagnosticLabels: Record<string,string> = {native:'Native app',worker:'Pinned worker',owner:'Owner / writer lease',resources:'Build reservation',game:'GAME / LIGHT mode',account:'Windows worker account',source:'Build source'};
export type Preflight = {schema:'OpenRemaster.DevPreflight.v1';scope:string|null;checked_at_ms:number;valid_for_ms:30000;can_submit:boolean;production_go:false;checks:{id:string;status:'PASS'|'BLOCKED'|'UNKNOWN';detail:string;next_step:string}[]};
export function parsePreflight(raw: unknown, scope: unknown): Preflight {
  const value=raw as Preflight;
  if (!value || value.schema!=='OpenRemaster.DevPreflight.v1' || value.scope!==scope || value.production_go!==false
      || !Number.isSafeInteger(value.checked_at_ms) || value.checked_at_ms<0 || value.valid_for_ms!==30000 || typeof value.can_submit!=='boolean'
      || !Array.isArray(value.checks) || value.checks.length!==diagnosticIds.length) throw Error('Invalid build diagnostic');
  for (const id of diagnosticIds) {
    const rows=value.checks.filter(row=>row?.id===id);
    if (rows.length!==1 || !['PASS','BLOCKED','UNKNOWN'].includes(rows[0].status)
        || typeof rows[0].detail!=='string' || rows[0].detail.length>1024 || typeof rows[0].next_step!=='string' || rows[0].next_step.length>1024) throw Error('Invalid diagnostic check');
  }
  if (value.can_submit && value.checks.some(row=>row.status!=='PASS')) throw Error('Incomplete admission cannot enable a build');
  return value;
}
export function preflightFresh(value: Preflight|undefined, now=Date.now()) {
  return !!value && now>=value.checked_at_ms && now-value.checked_at_ms<value.valid_for_ms;
}
export function preflightAllowsSubmit(value: Preflight|undefined, now=Date.now()) {
  return preflightFresh(value,now) && value?.can_submit===true;
}

const object=(raw:unknown):Record<string,any>=>{if(!raw||typeof raw!=='object'||Array.isArray(raw))throw Error('Invalid log response');return raw as Record<string,any>;};
const hex=(v:unknown)=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
const maxBytes=64*1024*1024+131072;
export type LogSource='live'|'archive'|'bundle';
export type LogPage={source:LogSource;name:string;offset:number;next_offset:number;total_bytes:number;bytes:Uint8Array;eof:boolean;verified:boolean;file_sha256:string|null};
export async function bytesDigest(bytes: Uint8Array) {
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes.slice().buffer)),b=>b.toString(16).padStart(2,'0')).join('');
}
export async function parseLogPage(raw:unknown, operation:string, scope:string, evidence:string, source:LogSource, name:string, offset:number, manifest?:string):Promise<LogPage> {
  if(typeof raw!=='string'||raw.length>2*1024*1024)throw Error('Invalid log page size');
  const v=object(JSON.parse(raw));
  if(v.schema!=='OpenRemaster.DevLogPage.v1'||v.operation_id!==operation||v.scope!==scope||v.evidence_sha256!==evidence||v.production_go!==false
      ||v.source!==source||v.name!==name||v.offset!==offset||typeof v.bytes_base64!=='string'||v.bytes_base64.length>1398104
      ||!Number.isSafeInteger(v.total_bytes)||v.total_bytes<0||v.total_bytes>maxBytes||!Number.isSafeInteger(v.next_offset)
      ||typeof v.eof!=='boolean'||typeof v.verified!=='boolean'||!hex(v.chunk_sha256))throw Error('Log page identity or bounds rejected');
  const bytes=Uint8Array.from(atob(v.bytes_base64),c=>c.charCodeAt(0));
  if(bytes.length>1024*1024||v.next_offset!==offset+bytes.length||offset<0||v.next_offset>v.total_bytes
      ||v.eof!==(v.next_offset===v.total_bytes)||(!v.eof&&!bytes.length))throw Error('Invalid log page progress');
  if(source==='live'?(v.verified!==false||v.file_sha256!==null||v.manifest_sha256!==null):(!v.verified||!hex(v.file_sha256)||v.manifest_sha256!==manifest))throw Error('Invalid log verification scope');
  if(await bytesDigest(bytes)!==v.chunk_sha256)throw Error('Log page checksum mismatch');
  return {...v,bytes} as LogPage;
}
export type LogExport={bytes:number;sha256:string;manifest_sha256:string};
export function parseLogExport(raw:unknown,operation:string,scope:string,evidence:string):LogExport {
  if(typeof raw!=='string'||raw.length>8192)throw Error('Invalid export response');
  const v=object(JSON.parse(raw));
  if(v.schema!=='OpenRemaster.DevLogExport.v1'||v.operation_id!==operation||v.scope!==scope||v.evidence_sha256!==evidence||v.production_go!==false
      ||!hex(v.sha256)||!hex(v.manifest_sha256)||!Number.isSafeInteger(v.bytes)||v.bytes<1||v.bytes>maxBytes)throw Error('Invalid diagnostic export identity');
  return v as LogExport;
}
export function filterLog(text:string,query:string,level:string) {
  const needle=query.toLocaleLowerCase();
  return text.split(/\r?\n/).filter(line=>(!needle||line.toLocaleLowerCase().includes(needle))
    &&(level==='all'||(level==='error'?/error|fatal|exception/i:/warn/i).test(line))).join('\n');
}
