//! Isolated source candidate. No catalog, installation or runtime admission.
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Selection {
    project_id: String,
    edition_id: String,
    committed_operation_id: String,
    accepted_manifest_digest: String,
}

fn id(s: &str) -> bool {
    !s.is_empty() && s.len() <= 64 && s.bytes().all(|b| b.is_ascii_alphanumeric() || b"_-".contains(&b))
}
fn hex(s: &str, n: usize) -> bool {
    s.len() == n && s.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}
impl Selection {
    fn valid(&self) -> bool {
        id(&self.project_id) && id(&self.edition_id) &&
        hex(&self.committed_operation_id, 32) && hex(&self.accepted_manifest_digest, 64)
    }
}
fn now_ms() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_millis() as u64).unwrap_or(0)
}
pub fn hold(reason: &str) -> Value {
    json!({"schema":"OpenRemaster.NativeFileObservation.v1", "state":"HOLD", "reason":reason,
        "read_only":true,"execution_authority":false,"gameplay":"UNKNOWN","fidelity":"UNKNOWN",
        "observed_epoch_ms":now_ms()})
}

#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Held {
    schema: String, state: String, reason: String, read_only: bool, execution_authority: bool,
    gameplay: String, fidelity: String, observed_epoch_ms: u64,
}
#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct ObservedFile {
    role: String, name: String, volume: String, file_id: String, bytes: u64, sha256: String,
}
#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Live {
    schema: String, state: String, read_only: bool, execution_authority: bool,
    gameplay: String, fidelity: String, observed_epoch_ms: u64, selection: Selection,
    engine: String, source_commit: String, source_tree: String,
    source_manifest_sha256: String, build_plan_sha256: String, files: Vec<ObservedFile>,
}
fn common(schema: &str, readonly: bool, authority: bool, gameplay: &str, fidelity: &str, at: u64, now: u64) -> bool {
    schema == "OpenRemaster.NativeFileObservation.v1" && readonly && !authority &&
    gameplay == "UNKNOWN" && fidelity == "UNKNOWN" && at <= now && now - at <= 5000
}
fn response(raw: &[u8], selection: &Selection, now: u64) -> Result<Value, String> {
    // Typed deserialization from original bytes rejects duplicate fields,
    // unknown fields and trailing JSON. Do not parse into Value first.
    if raw.is_empty() || raw.len() > 4096 || raw.last() != Some(&b'\n') ||
        !raw[..raw.len()-1].iter().all(|b| (0x20..=0x7e).contains(b)) {
        return Err("OBSERVATION_FRAMING".into());
    }
    if let Ok(v) = serde_json::from_slice::<Held>(raw) {
        if v.state == "HOLD" && ["NO_ACCEPTED_SELECTION", "INVALID_REQUEST", "UNVERIFIED"].contains(&v.reason.as_str()) &&
            common(&v.schema, v.read_only, v.execution_authority, &v.gameplay, &v.fidelity, v.observed_epoch_ms, now) {
            return serde_json::to_value(v).map_err(|_| "OBSERVATION_JSON".into());
        }
    }
    let v: Live = serde_json::from_slice(raw).map_err(|_| "OBSERVATION_JSON")?;
    let mut identities = std::collections::BTreeSet::new();
    let mut names = std::collections::BTreeSet::new();
    let valid_file = |f: &ObservedFile| {
        !f.name.is_empty() && f.name.len() <= 120 &&
        (f.name.as_bytes()[0].is_ascii_alphanumeric() || b"_-".contains(&f.name.as_bytes()[0])) &&
        f.name.bytes().all(|b| b.is_ascii_alphanumeric() || b"._-".contains(&b)) &&
        ((f.role == "EXE" && f.name.to_ascii_lowercase().ends_with(".exe")) ||
         (f.role == "PCK" && f.name.to_ascii_lowercase().ends_with(".pck"))) &&
        f.bytes > 0 && f.bytes <= 268435456 && hex(&f.sha256, 64) && hex(&f.volume, 16) && hex(&f.file_id, 32)
    };
    if v.state != "LIVE" || !common(&v.schema,v.read_only,v.execution_authority,&v.gameplay,&v.fidelity,v.observed_epoch_ms,now) ||
        &v.selection != selection || !v.selection.valid() || !id(&v.engine) ||
        !hex(&v.source_commit,40) || !hex(&v.source_tree,40) || !hex(&v.source_manifest_sha256,64) || !hex(&v.build_plan_sha256,64) ||
        !(1..=2).contains(&v.files.len()) || v.files.iter().filter(|f| f.role == "EXE").count() != 1 ||
        v.files.iter().filter(|f| f.role == "PCK").count() > 1 ||
        !v.files.iter().all(valid_file) || v.files.iter().map(|f| f.bytes).sum::<u64>() > 268435456 ||
        !v.files.iter().all(|f| identities.insert(format!("{}:{}",f.volume,f.file_id)) && names.insert(f.name.to_ascii_lowercase())) {
        return Err("OBSERVATION_SCOPE".into());
    }
    // Expected source/manifest/file bytes/hash still require the independent
    // accepted UI binding. Native shape checks do not grant catalog authority.
    serde_json::to_value(v).map_err(|_| "OBSERVATION_JSON".into())
}

#[cfg(feature = "dev-worker")]
mod native {
    use super::*;
    use sha2::{Digest, Sha256};
    use std::{fs::{File, OpenOptions}, io::Read, os::windows::{fs::{MetadataExt, OpenOptionsExt}, io::AsRawHandle}, path::Path};
    const CONFIG: &str = include_str!("../local-status-v2-pins.json");
    const ENTRY: &str = "eb0631822500849f94cdfebc287dded5a958a08c555153e75b07804edbf84437";
    // Layout matches Win32 BY_HANDLE_FILE_INFORMATION (all fields are DWORD).
    #[repr(C)]
    struct Info { attributes:u32, creation:[u32;2], access:[u32;2], write:[u32;2], volume:u32,
        size_high:u32, size_low:u32, links:u32, index_high:u32, index_low:u32 }
    #[link(name="kernel32")]
    extern "system" { fn GetFileInformationByHandle(handle:*mut std::ffi::c_void, info:*mut Info) -> i32; }
    fn pin(path: &Path, digest: &str, bound: u64, locks: &mut Vec<File>) -> Result<Vec<u8>,String> {
        if !path.is_absolute() { return Err("OBSERVATION_PATH".into()); }
        // Hold every ancestor without FILE_SHARE_DELETE through child exit.
        // OPEN_REPARSE_POINT inspects the entry itself, not its redirect target.
        let mut parents:Vec<_> = path.ancestors().skip(1).collect(); parents.reverse();
        for parent in parents {
            let f = OpenOptions::new().access_mode(0x80).share_mode(3)
                .custom_flags(0x02000000 | 0x00200000).open(parent).map_err(|_| "OBSERVATION_ANCESTOR")?;
            let m = f.metadata().map_err(|_| "OBSERVATION_METADATA")?;
            if !m.is_dir() || m.file_attributes() & 0x400 != 0 { return Err("OBSERVATION_REPARSE".into()); }
            locks.push(f);
        }
        let mut f = OpenOptions::new().read(true).share_mode(1).custom_flags(0x00200000)
            .open(path).map_err(|_| "OBSERVATION_FILE")?;
        let m = f.metadata().map_err(|_| "OBSERVATION_METADATA")?;
        let mut info:Info = unsafe { std::mem::zeroed() };
        if !m.is_file() || m.file_attributes() & 0x400 != 0 || m.len() > bound ||
            unsafe { GetFileInformationByHandle(f.as_raw_handle(), &mut info) } == 0 || info.links != 1 {
            return Err("OBSERVATION_REGULAR_SINGLE_LINK".into());
        }
        let mut bytes=Vec::new(); (&mut f).take(bound+1).read_to_end(&mut bytes).map_err(|_| "OBSERVATION_READ")?;
        if bytes.len() as u64 != m.len() || format!("{:x}", Sha256::digest(&bytes)) != digest {
            return Err("OBSERVATION_PIN".into());
        }
        locks.push(f); Ok(bytes)
    }
    pub(super) fn call(selection: &Selection) -> Result<Value,String> {
        let config:Value = serde_json::from_str(CONFIG).map_err(|_| "OBSERVATION_CONFIG")?;
        let root = Path::new(config["root"].as_str().ok_or("OBSERVATION_ROOT")?);
        let python = Path::new(config["python"].as_str().ok_or("OBSERVATION_PYTHON")?);
        let entry = root.join("r8-observation").join("entry.py");
        let mut locks = Vec::new();
        pin(python,config["python_sha256"].as_str().ok_or("OBSERVATION_PYTHON_PIN")?,67108864,&mut locks)?;
        let bytes = pin(&entry,ENTRY,65536,&mut locks)?;
        let source = bytes.iter().map(|b| format!("{b:02x}")).collect::<String>();
        // Paths come only from compiled configuration, not renderer fields.
        let file_literal = serde_json::to_string(entry.to_str().ok_or("OBSERVATION_UTF8_PATH")?).map_err(|_| "OBSERVATION_PATH")?;
        let bootstrap = format!("__file__={file_literal};exec(compile(bytes.fromhex('{source}'),__file__,'exec'))");
        let input=serde_json::to_vec(selection).map_err(|_| "OBSERVATION_REQUEST")?;
        if input.len()>512 { return Err("OBSERVATION_REQUEST_SIZE".into()); }
        let (raw,success)=crate::dev_worker::call_python_output(&config,&["-B","-I","-S","-c",&bootstrap],&input,4096,5)?;
        if !success { return Err("OBSERVATION_CHILD_FAILED".into()); }
        // Locks remain in scope until the child and bounded pipe readers finish.
        let result=response(&raw,selection,now_ms()); drop(locks); result
    }
}

#[cfg(feature = "dev-worker")]
pub fn observe(selection: Selection) -> Value {
    if !selection.valid() { return hold("INVALID_REQUEST"); }
    native::call(&selection).unwrap_or_else(|_| hold("UNVERIFIED"))
}

// Source-only tests, deliberately NOT executed without native admission.
#[cfg(test)]
mod tests {
    use super::*;
    fn selected() -> Selection { Selection { project_id:"Fixture".into(),edition_id:"DEV".into(),
        committed_operation_id:"a".repeat(32),accepted_manifest_digest:"b".repeat(64) } }
    #[test] fn exact_request() {
        assert!(selected().valid()); let mut bad=selected(); bad.project_id="../x".into(); assert!(!bad.valid());
        assert!(serde_json::from_str::<Selection>(r#"{"project_id":"x","project_id":"y","edition_id":"d","committed_operation_id":"a","accepted_manifest_digest":"b"}"#).is_err());
    }
    #[test] fn strict_record() {
        let s=selected(); let raw=format!("{}\n",hold("UNVERIFIED")); let now=now_ms();
        assert!(response(raw.as_bytes(),&s,now).is_ok());
        assert!(response(raw.trim_end().as_bytes(),&s,now).is_err());
        assert!(response(format!("{raw}\n").as_bytes(),&s,now).is_err());
        let duplicated=raw.replace("\"state\":\"HOLD\"", "\"state\":\"HOLD\",\"state\":\"HOLD\"");
        assert!(response(duplicated.as_bytes(),&s,now).is_err());
    }
}
