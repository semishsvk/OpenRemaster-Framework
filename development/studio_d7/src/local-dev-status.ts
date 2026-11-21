export type KnowledgeState='NOT_REQUESTED'|'PENDING'|'RUNNING'|'VERIFIED'|'CHECKPOINT_PENDING';
export type LocalDevJob={operation_id:string;scenario:string;state:'QUEUED'|'STARTED'|'COMMITTED'|'HOLD'|'UNKNOWN'|'FAILED_SETTLED';
  original_state?:string;disposition?:{kind:'KNOWN_FAILED_SETTLED';state:'FAILED_SETTLED';receipt_sha256:string}|null;
  launch_count:number;project:string;knowledge:{state:KnowledgeState;project:string|null;attempts:number;reason?:string}};
export type LocalDevSnapshot={
  schema:'OpenRemaster.LocalStudioStatus.v1'|'OpenRemaster.LocalStudioStatus.v2'; captured_epoch:number; mode:'LOCAL_DEV'; source:'LOCAL_NATIVE_READONLY';
  read_only:true; azure_required:false; witness_required:false; production_go:false;
  host:{state:string;healthy:boolean;process_alive:boolean;heartbeat_age_seconds:number|null;generation:string|null};
  counts:{queued:number;running:number;committed:number;hold:number;failed_settled?:number;checkpoint_pending:number};
  jobs:LocalDevJob[];
};
const object=(x:unknown):x is Record<string,unknown>=>!!x&&typeof x==='object'&&!Array.isArray(x);
const integer=(x:unknown)=>Number.isSafeInteger(x)&&Number(x)>=0&&Number(x)<=10000000;
const text=(x:unknown,max:number):x is string=>typeof x==='string'&&x.length<=max;
export function localSnapshotFresh(snapshot:LocalDevSnapshot,now=Date.now()):boolean {
  const age=now/1000-snapshot.captured_epoch;
  return age>=-2&&age<=10;
}
export function parseLocalDevStatus(value:unknown,now=Date.now()):LocalDevSnapshot {
  if(!object(value))throw Error('Local DEV status unavailable: invalid response');
  if(!['OpenRemaster.LocalStudioStatus.v1','OpenRemaster.LocalStudioStatus.v2'].includes(String(value.schema)))
    throw Error('Local DEV status unavailable: unsupported response schema');
  const v2=value.schema==='OpenRemaster.LocalStudioStatus.v2';
  if(JSON.stringify(value).length>65536||
    value.mode!=='LOCAL_DEV'||value.source!=='LOCAL_NATIVE_READONLY'||value.read_only!==true||
    value.azure_required!==false||value.witness_required!==false||value.production_go!==false||
    typeof value.captured_epoch!=='number'||!Number.isFinite(value.captured_epoch)||!object(value.host)||
    !object(value.counts)||!Array.isArray(value.jobs)||value.jobs.length>12)throw Error('Invalid local DEV snapshot');
  const host=value.host;
  if(!['STOPPED','STARTING','IDLE','RUNNING','HOLD'].includes(String(host.state))||typeof host.healthy!=='boolean'||
    typeof host.process_alive!=='boolean'||!(host.generation===null||typeof host.generation==='string'&&/^[a-f0-9]{32}$/.test(host.generation))||
    !(host.heartbeat_age_seconds===null||typeof host.heartbeat_age_seconds==='number'&&Number.isFinite(host.heartbeat_age_seconds))||
    host.healthy&&(!host.process_alive||!['STARTING','IDLE','RUNNING'].includes(String(host.state))||
      typeof host.heartbeat_age_seconds!=='number'||host.heartbeat_age_seconds<0||host.heartbeat_age_seconds>6))throw Error('Invalid local host observation');
  for(const key of ['queued','running','committed','hold','checkpoint_pending'])if(!integer(value.counts[key]))throw Error('Invalid local job counts');
  if(v2&&!integer(value.counts.failed_settled))throw Error('Invalid settled failure count');
  if(!v2&&value.counts.failed_settled!==undefined)throw Error('Settlement fields require local DEV status v2');
  const seen=new Set<string>();
  for(const job of value.jobs){
    if(!object(job)||typeof job.operation_id!=='string'||!/^[a-f0-9]{32}$/.test(job.operation_id)||seen.has(job.operation_id)||
      typeof job.scenario!=='string'||!/^(check_local_dev|build_[a-z0-9-]+_dev)$/.test(job.scenario)||job.scenario.length>100||
      !(v2?['QUEUED','STARTED','COMMITTED','HOLD','UNKNOWN','FAILED_SETTLED']:['QUEUED','STARTED','COMMITTED','HOLD','UNKNOWN']).includes(String(job.state))||![0,1].includes(Number(job.launch_count))||
      typeof job.launch_count!=='number'||!text(job.project,100)||!object(job.knowledge))throw Error('Invalid local job observation');
    seen.add(job.operation_id);
    const knowledge=job.knowledge;
    if(!['NOT_REQUESTED','PENDING','RUNNING','VERIFIED','CHECKPOINT_PENDING'].includes(String(knowledge.state))||
      !(knowledge.project===null||text(knowledge.project,100))||!integer(knowledge.attempts)||
      !(knowledge.reason===undefined||text(knowledge.reason,180)))throw Error('Invalid checkpoint observation');
    if(v2){
      if(job.state==='FAILED_SETTLED'){
        const disposition=job.disposition;
        if(job.launch_count!==1||job.original_state!=='HOLD'||!object(disposition)||disposition.kind!=='KNOWN_FAILED_SETTLED'||
          disposition.state!=='FAILED_SETTLED'||typeof disposition.receipt_sha256!=='string'||
          !/^[a-f0-9]{64}$/.test(disposition.receipt_sha256)||knowledge.state!=='NOT_REQUESTED'||
          knowledge.attempts!==0||knowledge.project!==null)throw Error('Invalid settled failure evidence');
      }else if(job.original_state!==job.state||job.disposition!==null)throw Error('Invalid original job state');
    }else if(job.original_state!==undefined||job.disposition!==undefined){
      throw Error('Settlement fields require local DEV status v2');
    }
  }
  const snapshot=value as LocalDevSnapshot;
  if(!localSnapshotFresh(snapshot,now))throw Error('Local DEV snapshot expired');
  return snapshot;
}
