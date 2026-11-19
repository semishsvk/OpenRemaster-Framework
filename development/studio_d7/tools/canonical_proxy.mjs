// Explicit headless TEST lab only. One fixed HTTP call, no process or dispatch.
import http from 'node:http';
const raw=process.env.ORF_CANONICAL_TEST_PORT;
if(raw!==undefined&&!/^[1-9]\d{0,4}$/.test(raw))throw Error('TEST_PORT');
const port=raw===undefined?null:Number(raw);
if(port!==null&&port>65535)throw Error('TEST_PORT');
let active=0;
export async function canonicalRoute(req,res){
 if(port===null||!['/api/canonical-core/context','/api/canonical-core/review'].includes(req.url))return false;
 if(req.method!=='GET'){res.writeHead(405);res.end();return true;}
 const getSingle=name=>{const values=[];for(let i=0;i<req.rawHeaders.length;i+=2)if(req.rawHeaders[i].toLowerCase()===name)values.push(req.rawHeaders[i+1]);return values.length===1?values[0]:null;};
 const context=req.url.endsWith('/context');const id=getSingle('x-orf-request'),release=getSingle('x-orf-release');
 if(req.headers['transfer-encoding']||req.headers['content-length']&&req.headers['content-length']!=='0'||!context&&(!/^[a-f0-9]{64}$/.test(id??'')||!/^[a-f0-9]{64}$/.test(release??''))){res.writeHead(400);res.end();return true;}
 if(active>=8){res.writeHead(503);res.end();return true;}active++;
 const body=JSON.stringify(context?{}:{request_id:id,expected_release_sha256:release});
 try{
  const answer=await new Promise((resolve,reject)=>{
   const call=http.request({host:'127.0.0.1',port,path:context?'/v1/core/context':'/v1/core/review',method:'POST',maxHeaderSize:16384,headers:{Authorization:'Bearer '+'v'.repeat(32),'Content-Type':'application/json','Content-Length':Buffer.byteLength(body),Connection:'close'}},reply=>{
    const parts=[];let bytes=0;
    reply.on('data',data=>{bytes+=data.length;if(bytes>16384)reply.destroy(Error('RESPONSE_SIZE'));else parts.push(data);});
    reply.on('error',reject);reply.on('end',()=>resolve({status:reply.statusCode,type:reply.headers['content-type'],body:Buffer.concat(parts)}));
   });
   const timer=setTimeout(()=>call.destroy(Error('TEST_DEADLINE')),2500);call.on('close',()=>clearTimeout(timer));call.on('error',reject);call.end(body);
  });
  res.writeHead(answer.status,{'Content-Type':answer.type??'application/octet-stream','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(answer.body);
 }catch{if(!res.headersSent){res.writeHead(503,{'Content-Type':'application/json'});res.end('{"status":"HOLD_NO_AUTO_RETRY"}');}}
 finally{active--;}
 return true;
}
