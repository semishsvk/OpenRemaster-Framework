import {parseSnapshotJson} from './snapshot-json.ts';
const STORED={
 inspector:['/stored/inspector-observation.json',131072],
 crossplane:['/stored/crossplane-observation.json',131072],
 plan:['/stored/bounded-plan-evidence.json',32768],
 completion:['/stored/game-completion-board.json',32000],
 replay:['/stored/host-connector-evidence.json',40000],
} as const;
export async function readStoredResponse(response:Response,limit:number,signal?:AbortSignal):Promise<unknown>{
 if(!Number.isSafeInteger(limit)||limit<1||limit>131072)throw Error('LIMIT');
 if(response.status!==200 || !/^application\/json(?:\s*;\s*charset\s*=\s*(?:"utf-8"|utf-8))?$/i.test(response.headers.get('content-type')?.trim()??'')){
  void response.body?.cancel().catch(()=>{});throw Error('HTTP_JSON_REQUIRED');
 }
 if(!response.body)throw Error('BODY_REQUIRED');
 const reader=response.body.getReader(),decoder=new TextDecoder('utf-8',{fatal:true});let bytes=0,text='',complete=false;
 const cancel=()=>{void reader.cancel().catch(()=>{});};signal?.addEventListener('abort',cancel,{once:true});
 try{
  while(true){signal?.throwIfAborted();const {done,value}=await reader.read();signal?.throwIfAborted();if(done){complete=true;break;}bytes+=value.byteLength;if(bytes>limit)throw Error('SIZE');text+=decoder.decode(value,{stream:true});}
  text+=decoder.decode();signal?.throwIfAborted();return parseSnapshotJson(text);
 }finally{signal?.removeEventListener('abort',cancel);if(!complete)cancel();reader.releaseLock();}
}
export async function loadStoredJson(key:keyof typeof STORED):Promise<unknown>{
 if(!Object.hasOwn(STORED,key))throw Error('UNKNOWN_ARCHIVE');
 const [url,limit]=STORED[key],controller=new AbortController();let timer:ReturnType<typeof setTimeout>|undefined;
 const deadline=new Promise<never>((_,reject)=>{timer=setTimeout(()=>{controller.abort();reject(Error('ARCHIVE_TIMEOUT'));},5000);});
 const operation=(async()=>readStoredResponse(await fetch(url,{method:'GET',cache:'no-store',redirect:'error',signal:controller.signal}),limit,controller.signal))();
 try{return await Promise.race([operation,deadline]);}finally{clearTimeout(timer);}
}
