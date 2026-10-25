use sha2::{Digest,Sha256};
use std::{fs,io::Read,path::PathBuf,process::{Command,Stdio},os::windows::process::CommandExt};
const CONFIG:&str=include_str!("../../WORKER-CONFIG.json");
fn hash(path:&PathBuf)->Result<String,String>{let mut file=fs::File::open(path).map_err(|e|e.to_string())?;let mut h=Sha256::new();let mut buffer=[0u8;65536];loop{let n=file.read(&mut buffer).map_err(|e|e.to_string())?;if n==0{break;}h.update(&buffer[..n]);}Ok(format!("{:x}",h.finalize()))}
fn run()->Result<i32,String>{
 let config:serde_json::Value=serde_json::from_str(CONFIG).map_err(|e|e.to_string())?;
 if config["profile"]!="DEV_UNSIGNED"||config["production_go"]!=false{return Err("DEV_SCOPE_REQUIRED".into());}
 let root=PathBuf::from(config["root"].as_str().ok_or("ROOT_REQUIRED")?);
 if !root.is_absolute(){return Err("ABSOLUTE_ROOT_REQUIRED".into());}
 let actual=root.join("WORKER-CONFIG.json");let expected=format!("{:x}",Sha256::digest(CONFIG.as_bytes()));
 if hash(&actual)?!=expected{return Err("WORKER_CONFIG_CHANGED".into());}
 for item in config["files"].as_array().ok_or("PINS_REQUIRED")?{
  let path=PathBuf::from(item["path"].as_str().ok_or("PIN_PATH_REQUIRED")?);
  if !path.is_absolute()||hash(&path)?!=item["sha256"].as_str().ok_or("PIN_SHA_REQUIRED")?{return Err("NATIVE_WORKER_PIN_CHANGED".into());}
 }
 let python=config["python"].as_str().ok_or("PYTHON_REQUIRED")?;
 let status=Command::new(python).args(["-B","-I"]).arg(root.join("host.py")).args(["daemon","--expected-config-sha",&expected]).current_dir(&root).stdin(Stdio::null()).stdout(Stdio::inherit()).stderr(Stdio::inherit()).creation_flags(0x08000000).status().map_err(|e|e.to_string())?;
 Ok(status.code().unwrap_or(75))
}
fn main(){match run(){Ok(code)=>std::process::exit(code),Err(error)=>{eprintln!("DEV_NATIVE_WORKER_HOLD: {}",error);std::process::exit(75);}}}
