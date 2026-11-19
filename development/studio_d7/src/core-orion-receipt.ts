/** Fixed, flat read-only projection. Parsing never confers authority. */
export type Receipt={schema:string;status:string;signatureCount:number;fixtureSha256:string;project:string;runId:string;clockMode:string;sourceMode:string;productionAdmission:string;dispatchAuthorized:boolean;automaticRetry:boolean;productionSigning:boolean;modelInvoked:boolean;workerStarted:boolean;journalWritten:boolean};
const MAX=8192;
export function parseReceipt(text:string):Receipt{
 if(new TextEncoder().encode(text).length>MAX)throw Error('SIZE');
 let i=0;const result:Record<string,unknown>=Object.create(null),seen=new Set<string>();
 const space=()=>{while(/[\x20\t\r\n]/.test(text[i]??'!'))i++;};
 function string():string{
  const start=i;if(text[i++]!=='"')throw Error('STRING');
  while(i<text.length){const ch=text[i++];if(ch==='\\'){i++;continue;}if(ch==='"')return JSON.parse(text.slice(start,i));}
  throw Error('STRING');
 }
 space();if(text[i++]!=='{')throw Error('OBJECT');space();
 if(text[i]!=='}')while(true){
  const key=string();if(seen.has(key))throw Error('DUPLICATE_KEY');seen.add(key);space();if(text[i++]!==':')throw Error('COLON');space();
  let value:unknown;if(text[i]==='"')value=string();else{
   const token=/^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/.exec(text.slice(i));
   if(!token)throw Error('PRIMITIVE');i+=token[0].length;value=JSON.parse(token[0]);
  }
  result[key]=value;space();if(text[i]===','){i++;space();continue;}break;
 }
 if(text[i++]!=='}')throw Error('OBJECT_END');space();if(i!==text.length)throw Error('TRAILING');
 const v=result,keys='schema status signatureCount fixtureSha256 project runId clockMode sourceMode productionAdmission dispatchAuthorized automaticRetry productionSigning modelInvoked workerStarted journalWritten'.split(' ');
 if(Object.keys(v).sort().join()!==keys.sort().join() || v.schema!=='ORF.CoreOrion.Readonly.v1' || v.status!=='VERIFIED_TEST_RECEIPT_HOLD' || v.signatureCount!==3 || typeof v.fixtureSha256!=='string' || !/^[a-f0-9]{64}$/.test(v.fixtureSha256) || typeof v.project!=='string' || !/^[\x20-\x7e]{1,256}$/.test(v.project) || typeof v.runId!=='string' || !/^[\x20-\x7e]{1,256}$/.test(v.runId) || v.clockMode!=='SAVED_SYNTHETIC_FIXTURE_TIME' || v.sourceMode!=='CORE_EXTENSION_EXISTING_ORION_VERIFIER' || v.productionAdmission!=='HOLD_NO_AUTO_RETRY')throw Error('SHAPE');
 for(const k of ['dispatchAuthorized','automaticRetry','productionSigning','modelInvoked','workerStarted','journalWritten'])if(v[k]!==false)throw Error('AUTHORITY');
 return v as Receipt;
}
export async function readReceipt(response:Response):Promise<Receipt>{
 if(response.status!==200 || !/^application\/json(?:\s*;\s*charset\s*=\s*(?:"utf-8"|utf-8))?$/i.test(response.headers.get('content-type')?.trim()??'')){
  void response.body?.cancel().catch(()=>{});throw Error('HTTP');
 }
 if(!response.body)throw Error('BODY');
 const reader=response.body.getReader(),decoder=new TextDecoder('utf-8',{fatal:true});let bytes=0,text='',complete=false;
 try{
  while(true){const {done,value}=await reader.read();if(done){complete=true;break;}bytes+=value.byteLength;if(bytes>MAX)throw Error('SIZE');text+=decoder.decode(value,{stream:true});}
  text+=decoder.decode();return parseReceipt(text);
 }finally{if(!complete)void reader.cancel().catch(()=>{});reader.releaseLock();}
}
