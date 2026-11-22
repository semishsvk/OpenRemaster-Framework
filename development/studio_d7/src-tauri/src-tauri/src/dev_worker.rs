use serde::Deserialize;
use sha2::{Digest,Sha256};
use std::{fs,io::Read,path::PathBuf,process::{Command,Stdio},thread,time::{Duration,Instant,SystemTime,UNIX_EPOCH}};
use std::os::windows::process::CommandExt;

const CONFIG:&str=include_str!("../dev-worker-pins.json");
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DevRequest{action:String,operation_id:String,scenario:String}
fn hash(path:&PathBuf)->Result<String,String>{
 let mut file=fs::File::open(path).map_err(|_|"PIN_FILE_UNAVAILABLE")?;
 let mut digest=Sha256::new();let mut buffer=[0u8;65536];
 loop{let n=file.read(&mut buffer).map_err(|_|"PIN_READ_FAILED")?;if n==0{break;}digest.update(&buffer[..n]);}
 Ok(format!("{:x}",digest.finalize()))
}
fn execute(request:DevRequest)->Result<String,String>{
 if !["submit","status"].contains(&request.action.as_str()) || !["normal","child","nonzero","timeout","crash_after_ack"].contains(&request.scenario.as_str())
  ||request.operation_id.len()!=32||!request.operation_id.bytes().all(|b|b.is_ascii_digit()||(b'a'..=b'f').contains(&b)){return Err("DEV_REQUEST_DENIED".into());}
 let pins:serde_json::Value=serde_json::from_str(CONFIG).map_err(|_|"DEV_CONFIG_INVALID")?;
 let string=|name:&str|pins[name].as_str().ok_or("DEV_CONFIG_FIELD_MISSING");
 let root=PathBuf::from(string("root")?);
 if !root.is_absolute(){return Err("DEV_ROOT_NOT_ABSOLUTE".into());}
 let python=PathBuf::from(string("python")?);let broker=root.join("broker.py");let manifest=root.join("BROKER-PINS.json");
 for (path,key) in [(&python,"python_sha256"),(&broker,"broker_sha256"),(&manifest,"manifest_sha256")]{
  if hash(path)?!=string(key)?{return Err("DEV_PIN_CHANGED".into());}
 }
 let folder=root.join("ipc-logs");fs::create_dir_all(&folder).map_err(|_|"DEV_LOG_DIRECTORY")?;
 let stamp=SystemTime::now().duration_since(UNIX_EPOCH).map_err(|_|"DEV_CLOCK")?.as_nanos();
 let out=folder.join(format!("{}-{}.stdout",request.operation_id,stamp));let err=folder.join(format!("{}-{}.stderr",request.operation_id,stamp));
 let create=|path:&PathBuf|fs::OpenOptions::new().write(true).create_new(true).open(path).map_err(|_|"DEV_LOG_CREATE");
 let raw=serde_json::json!({"action":request.action,"operation_id":request.operation_id,"scenario":request.scenario}).to_string();
 let mut child=Command::new(&python).arg("-B").arg("-I").arg(&broker).arg("--request").arg(raw)
  .current_dir(&root).stdin(Stdio::null()).stdout(Stdio::from(create(&out)?)).stderr(Stdio::from(create(&err)?))
  .creation_flags(0x08000000).spawn().map_err(|_|"DEV_BROKER_START_FAILED")?;
 let started=Instant::now();
 let status=loop{
  match child.try_wait(){Ok(Some(status))=>break status,Ok(None)=>{},Err(_)=>{let _=child.kill();let _=child.wait();return Err("DEV_BROKER_WAIT_FAILED".into());}}
  if started.elapsed()>Duration::from_secs(45)||fs::metadata(&out).map(|m|m.len()).unwrap_or(0)>65536||fs::metadata(&err).map(|m|m.len()).unwrap_or(0)>65536{
   let _=child.kill();let _=child.wait();return Err("DEV_BROKER_BOUND_HOLD".into());
  }
  thread::sleep(Duration::from_millis(30));
 };
 if !status.success(){return Err("DEV_BROKER_EXITED_QUERY_SAVED_OPERATION".into());}
 let raw=fs::read_to_string(out).map_err(|_|"DEV_RESPONSE_READ")?;
 let value:serde_json::Value=serde_json::from_str(&raw).map_err(|_|"DEV_RESPONSE_JSON")?;
 if value["production_go"]!=false||value["schema"]!="OpenRemaster.DevWorkflowResult.v1"{return Err("DEV_RESPONSE_SCOPE".into());}
 Ok(raw)
}
#[tauri::command]
pub async fn dev_worker_call(request:DevRequest)->Result<String,String>{
 tauri::async_runtime::spawn_blocking(move||execute(request)).await.map_err(|_|"DEV_COMMAND_PANIC".to_string())?
}

#[cfg(test)]
mod tests{
 use super::*;
 #[test]fn rejects_request_before_spawn(){
  assert!(execute(DevRequest{action:"submit".into(),operation_id:"../escape".into(),scenario:"normal".into()}).is_err());
  assert!(execute(DevRequest{action:"submit".into(),operation_id:"a".repeat(32),scenario:"shell".into()}).is_err());
 }
 #[test]fn extra_fields_are_denied(){
  assert!(serde_json::from_str::<DevRequest>(r#"{"action":"submit","operation_id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","scenario":"normal","path":"F:/production"}"#).is_err());
 }
}
