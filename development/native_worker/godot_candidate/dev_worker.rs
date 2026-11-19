use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::os::windows::process::CommandExt;
use std::{
    fs,
    io::Read,
    path::PathBuf,
    process::{Command, Stdio},
    thread,
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

const CONFIG: &str = include_str!("../dev-worker-pins.json");
#[derive(Deserialize, Clone)]
#[serde(deny_unknown_fields)]
pub struct DevRequest {
    action: String,
    operation_id: String,
    scenario: String,
    #[serde(default)]
    dev_packet_path: Option<String>,
    #[serde(default)]
    dev_receipt_path: Option<String>,
    #[serde(default)]
    dev_receipt_sha256: Option<String>,
}
fn hash(path: &PathBuf) -> Result<String, String> {
    let mut file = fs::File::open(path).map_err(|_| "PIN_FILE_UNAVAILABLE")?;
    let mut digest = Sha256::new();
    let mut buffer = [0u8; 65536];
    loop {
        let n = file.read(&mut buffer).map_err(|_| "PIN_READ_FAILED")?;
        if n == 0 {
            break;
        }
        digest.update(&buffer[..n]);
    }
    Ok(format!("{:x}", digest.finalize()))
}
fn verify_dev_receipt(
    root: &PathBuf,
    python: &PathBuf,
    pins: &serde_json::Value,
    request: &DevRequest,
) -> Result<String, String> {
    let string = |name: &str| pins[name].as_str().ok_or("DEV_CONFIG_FIELD_MISSING");
    let configured = PathBuf::from(string("dev_receipt")?);
    let receipt = if let Some(path) = &request.dev_receipt_path {
        PathBuf::from(path)
    } else {
        configured
    };
    let packet = if let Some(path) = &request.dev_packet_path {
        PathBuf::from(path)
    } else {
        PathBuf::from(string("dev_packet")?)
    };
    let verifier = PathBuf::from(string("dev_self_signed_verifier")?);
    for path in [&receipt, &packet, &verifier] {
        if !path.is_absolute() {
            return Err("DEV_RECEIPT_PATH_NOT_ABSOLUTE".into());
        }
        if !path.exists() {
            return Err("DEV_RECEIPT_REQUIRED".into());
        }
    }
    let root = fs::canonicalize(root).map_err(|_| "DEV_ROOT_NOT_FOUND")?;
    let packet = fs::canonicalize(packet).map_err(|_| "DEV_PACKET_REQUIRED")?;
    let receipt = fs::canonicalize(receipt).map_err(|_| "DEV_RECEIPT_REQUIRED")?;
    if !packet.starts_with(&root) {
        return Err("DEV_PACKET_PATH_OUTSIDE_ROOT".into());
    }
    if !receipt.starts_with(&root) {
        return Err("DEV_RECEIPT_PATH_OUTSIDE_ROOT".into());
    }
    let receipt_hash = hash(&receipt)?;
    let expected = request
        .dev_receipt_sha256
        .as_deref()
        .unwrap_or(string("dev_receipt_sha256")?);
    if receipt_hash != expected {
        return Err("DEV_RECEIPT_HASH_MISMATCH".into());
    }
    let packet_json: serde_json::Value =
        serde_json::from_slice(&fs::read(&packet).map_err(|_| "DEV_PACKET_READ_FAILED")?)
            .map_err(|_| "DEV_PACKET_JSON")?;
    if request.scenario == "build_godot_dev" {
        let project = pins["godot_project_id"].as_str().filter(|s| !s.is_empty()).ok_or("GODOT_PROJECT_PIN_REQUIRED")?;
        let source = pins["godot_source_ref"].as_str().filter(|s| !s.is_empty()).ok_or("GODOT_SOURCE_PIN_REQUIRED")?;
        if packet_json["work_package"]["capability"] != "DEV_UNSIGNED_GODOT_BUILD"
            || packet_json["work_package"]["project_id"] != project
            || packet_json["work_package"]["source"] != source {
            return Err("GODOT_PROJECT_SCOPED_PACKET_REQUIRED".into());
        }
    }
    if packet_json["operation_id"] != request.operation_id {
        return Err("DEV_PACKET_OPERATION_MISMATCH".into());
    }
    let receipt_json: serde_json::Value =
        serde_json::from_slice(&fs::read(&receipt).map_err(|_| "DEV_RECEIPT_READ_FAILED")?)
            .map_err(|_| "DEV_RECEIPT_JSON")?;
    if receipt_json["operation_id"] != request.operation_id {
        return Err("DEV_RECEIPT_OPERATION_MISMATCH".into());
    }
    if hash(&verifier)? != string("dev_self_signed_verifier_sha256")? {
        return Err("DEV_RECEIPT_VERIFIER_PIN_CHANGED".into());
    }
    let output = Command::new(python)
        .arg("-B")
        .arg("-I")
        .arg(&verifier)
        .arg("verify")
        .arg("--packet")
        .arg(&packet)
        .arg("--receipt")
        .arg(&receipt)
        .output()
        .map_err(|_| "DEV_RECEIPT_VERIFIER_START_FAILED")?;
    if !output.status.success() {
        return Err("DEV_RECEIPT_SIGNATURE_INVALID".into());
    }
    let result: serde_json::Value =
        serde_json::from_slice(&output.stdout).map_err(|_| "DEV_RECEIPT_VERIFIER_RESPONSE")?;
    if result["status"] != "DEV_SELF_SIGNED_VALID"
        || result["authority_bound"] != false
        || result["production_go"] != false
    {
        return Err("DEV_RECEIPT_SCOPE_INVALID".into());
    }
    Ok(receipt_hash)
}
fn issue_ephemeral_receipt(
    root: &PathBuf,
    python: &PathBuf,
    pins: &serde_json::Value,
    request: &DevRequest,
) -> Result<DevRequest, String> {
    let string = |name: &str| pins[name].as_str().ok_or("DEV_CONFIG_FIELD_MISSING");
    let issuer = PathBuf::from(string("dev_self_signed_issuer")?);
    let template = PathBuf::from(string("dev_packet_template")?);
    if !issuer.is_absolute() || !template.is_absolute() {
        return Err("DEV_ISSUER_PATH_NOT_ABSOLUTE".into());
    }
    if !issuer.exists() || !template.exists() {
        return Err("DEV_ISSUER_REQUIRED".into());
    }
    if hash(&issuer)? != string("dev_self_signed_issuer_sha256")?
        || hash(&template)? != string("dev_packet_template_sha256")?
    {
        return Err("DEV_ISSUER_PIN_CHANGED".into());
    }
    let folder = root.join("state").join("dev-receipts");
    fs::create_dir_all(&folder).map_err(|_| "DEV_ISSUER_DIRECTORY")?;
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|_| "DEV_CLOCK")?
        .as_nanos();
    let packet = folder.join(format!("{}-{}.packet.json", request.operation_id, stamp));
    let receipt = folder.join(format!("{}-{}.receipt.json", request.operation_id, stamp));
    let output = Command::new(python)
        .arg("-B")
        .arg("-I")
        .arg(&issuer)
        .arg("issue")
        .arg("--template")
        .arg(&template)
        .arg("--operation-id")
        .arg(&request.operation_id)
        .arg("--packet-out")
        .arg(&packet)
        .arg("--receipt-out")
        .arg(&receipt)
        .output()
        .map_err(|_| "DEV_ISSUER_START_FAILED")?;
    if !output.status.success() {
        return Err("DEV_ISSUER_FAILED".into());
    }
    let result: serde_json::Value =
        serde_json::from_slice(&output.stdout).map_err(|_| "DEV_ISSUER_RESPONSE")?;
    if result["status"] != "DEV_EPHEMERAL_SELF_SIGNED_CREATED"
        || result["private_key_persisted"] != false
        || result["production_go"] != false
    {
        return Err("DEV_ISSUER_SCOPE_INVALID".into());
    }
    if !packet.exists() || !receipt.exists() {
        return Err("DEV_ISSUER_OUTPUT_MISSING".into());
    }
    let mut generated = request.clone();
    generated.dev_packet_path = Some(packet.display().to_string());
    generated.dev_receipt_path = Some(receipt.display().to_string());
    generated.dev_receipt_sha256 = Some(hash(&receipt)?);
    Ok(generated)
}
fn execute(request: DevRequest) -> Result<String, String> {
    if !["submit", "status"].contains(&request.action.as_str())
        || !["build_studio_dev", "build_godot_dev"]
            .contains(&request.scenario.as_str())
        || request.operation_id.len() != 32
        || !request
            .operation_id
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Err("DEV_REQUEST_DENIED".into());
    }
    let pins: serde_json::Value = serde_json::from_str(CONFIG).map_err(|_| "DEV_CONFIG_INVALID")?;
    let string = |name: &str| pins[name].as_str().ok_or("DEV_CONFIG_FIELD_MISSING");
    let root = PathBuf::from(string("root")?);
    if !root.is_absolute() {
        return Err("DEV_ROOT_NOT_ABSOLUTE".into());
    }
    let python = PathBuf::from(string("python")?);
    let broker = root.join("broker.py");
    let manifest = root.join("BROKER-PINS.json");
    for (path, key) in [
        (&python, "python_sha256"),
        (&broker, "broker_sha256"),
        (&manifest, "manifest_sha256"),
    ] {
        if hash(path)? != string(key)? {
            return Err("DEV_PIN_CHANGED".into());
        }
    }
    let request = if request.dev_receipt_path.is_none() && request.dev_receipt_sha256.is_none() {
        issue_ephemeral_receipt(&root, &python, &pins, &request)?
    } else {
        request
    };
    let dev_receipt_hash = verify_dev_receipt(&root, &python, &pins, &request)?;
    let folder = root.join("ipc-logs");
    fs::create_dir_all(&folder).map_err(|_| "DEV_LOG_DIRECTORY")?;
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|_| "DEV_CLOCK")?
        .as_nanos();
    let out = folder.join(format!("{}-{}.stdout", request.operation_id, stamp));
    let err = folder.join(format!("{}-{}.stderr", request.operation_id, stamp));
    let create = |path: &PathBuf| {
        fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)
            .map_err(|_| "DEV_LOG_CREATE")
    };
    let raw=serde_json::json!({"action":request.action,"operation_id":request.operation_id,"scenario":request.scenario}).to_string();
    let mut child = Command::new(&python)
        .arg("-B")
        .arg("-I")
        .arg(&broker)
        .arg("--request")
        .arg(raw)
        .current_dir(&root)
        .stdin(Stdio::null())
        .stdout(Stdio::from(create(&out)?))
        .stderr(Stdio::from(create(&err)?))
        .creation_flags(0x08000000)
        .spawn()
        .map_err(|_| "DEV_BROKER_START_FAILED")?;
    let started = Instant::now();
    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break status,
            Ok(None) => {}
            Err(_) => {
                let _ = child.kill();
                let _ = child.wait();
                return Err("DEV_BROKER_WAIT_FAILED".into());
            }
        }
        if started.elapsed() > Duration::from_secs(45)
            || fs::metadata(&out).map(|m| m.len()).unwrap_or(0) > 65536
            || fs::metadata(&err).map(|m| m.len()).unwrap_or(0) > 65536
        {
            let _ = child.kill();
            let _ = child.wait();
            return Err("DEV_BROKER_BOUND_HOLD".into());
        }
        thread::sleep(Duration::from_millis(30));
    };
    if !status.success() {
        return Err("DEV_BROKER_EXITED_QUERY_SAVED_OPERATION".into());
    }
    let raw = fs::read_to_string(out).map_err(|_| "DEV_RESPONSE_READ")?;
    let value: serde_json::Value = serde_json::from_str(&raw).map_err(|_| "DEV_RESPONSE_JSON")?;
    if value["production_go"] != false || value["schema"] != "OpenRemaster.DevWorkflowResult.v1" {
        return Err("DEV_RESPONSE_SCOPE".into());
    }
    let mut value = value;
    value["dev_receipt_verified"] = serde_json::Value::Bool(true);
    value["dev_receipt_scope"] = serde_json::Value::String("DEV_SELF_SIGNED".into());
    value["dev_receipt_sha256"] = serde_json::Value::String(dev_receipt_hash);
    Ok(value.to_string())
}
#[tauri::command]
pub async fn dev_worker_call(request: DevRequest) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || execute(request))
        .await
        .map_err(|_| "DEV_COMMAND_PANIC".to_string())?
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rejects_request_before_spawn() {
        assert!(execute(DevRequest {
            action: "submit".into(),
            operation_id: "../escape".into(),
            scenario: "normal".into(),
            dev_packet_path: None,
            dev_receipt_path: None,
            dev_receipt_sha256: None
        })
        .is_err());
        assert!(execute(DevRequest {
            action: "submit".into(),
            operation_id: "a".repeat(32),
            scenario: "shell".into(),
            dev_packet_path: None,
            dev_receipt_path: None,
            dev_receipt_sha256: None
        })
        .is_err());
    }
    #[test]
    fn extra_fields_are_denied() {
        assert!(serde_json::from_str::<DevRequest>(r#"{"action":"submit","operation_id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","scenario":"normal","path":"F:/production"}"#).is_err());
    }

    #[test]
    fn valid_pinned_receipt_is_bound_to_request() {
        let pins: serde_json::Value = serde_json::from_str(CONFIG).expect("valid pins");
        let root = PathBuf::from(pins["root"].as_str().expect("root"));
        let python = PathBuf::from(pins["python"].as_str().expect("python"));
        let request = DevRequest {
            action: "status".into(),
            operation_id: "a7d7c0de202510250000000000000001".into(),
            scenario: "normal".into(),
            dev_packet_path: Some(pins["dev_packet"].as_str().expect("packet").into()),
            dev_receipt_path: None,
            dev_receipt_sha256: Some(
                pins["dev_receipt_sha256"]
                    .as_str()
                    .expect("receipt hash")
                    .into(),
            ),
        };
        assert!(verify_dev_receipt(&root, &python, &pins, &request).is_ok());
    }

    #[test]
    fn mismatched_receipt_digest_is_denied_before_spawn() {
        let pins: serde_json::Value = serde_json::from_str(CONFIG).expect("valid pins");
        let root = PathBuf::from(pins["root"].as_str().expect("root"));
        let python = PathBuf::from(pins["python"].as_str().expect("python"));
        let request = DevRequest {
            action: "status".into(),
            operation_id: "a7d7c0de202510250000000000000001".into(),
            scenario: "normal".into(),
            dev_packet_path: None,
            dev_receipt_path: None,
            dev_receipt_sha256: Some("0".repeat(64)),
        };
        assert_eq!(
            verify_dev_receipt(&root, &python, &pins, &request).unwrap_err(),
            "DEV_RECEIPT_HASH_MISMATCH"
        );
    }

    #[test]
    fn missing_receipt_is_denied_before_spawn() {
        let pins: serde_json::Value = serde_json::from_str(CONFIG).expect("valid pins");
        let root = PathBuf::from(pins["root"].as_str().expect("root"));
        let python = PathBuf::from(pins["python"].as_str().expect("python"));
        let request = DevRequest {
            action: "status".into(),
            operation_id: "a7d7c0de202510250000000000000001".into(),
            scenario: "normal".into(),
            dev_packet_path: None,
            dev_receipt_path: Some(
                root.join("dev-evidence/missing-receipt.json")
                    .display()
                    .to_string(),
            ),
            dev_receipt_sha256: None,
        };
        assert_eq!(
            verify_dev_receipt(&root, &python, &pins, &request).unwrap_err(),
            "DEV_RECEIPT_REQUIRED"
        );
    }

    #[test]
    fn production_marker_is_denied_before_spawn() {
        let pins: serde_json::Value = serde_json::from_str(CONFIG).expect("valid pins");
        let root = PathBuf::from(pins["root"].as_str().expect("root"));
        let python = PathBuf::from(pins["python"].as_str().expect("python"));
        let source = PathBuf::from(pins["dev_receipt"].as_str().expect("receipt"));
        let tampered = root.join("dev-evidence/rust-test-production-marker.json");
        let raw = fs::read_to_string(&source)
            .expect("receipt bytes")
            .replace("\"production_go\": false", "\"production_go\": true");
        fs::write(&tampered, raw).expect("tampered receipt");
        let request = DevRequest {
            action: "status".into(),
            operation_id: "a7d7c0de202510250000000000000001".into(),
            scenario: "normal".into(),
            dev_packet_path: None,
            dev_receipt_path: Some(tampered.display().to_string()),
            dev_receipt_sha256: Some(hash(&tampered).expect("tampered hash")),
        };
        let result = verify_dev_receipt(&root, &python, &pins, &request);
        let _ = fs::remove_file(&tampered);
        assert_eq!(result.unwrap_err(), "DEV_RECEIPT_SIGNATURE_INVALID");
    }

    #[test]
    #[ignore = "bounded native IPC status smoke; unified DEV broker; never submits a build"]
    fn runtime_smoke_returns_dev_scope() {
        let result = execute(DevRequest {
            action: "status".into(),
            operation_id: "a7d7c0de202510250000000000000001".into(),
            scenario: "build_studio_dev".into(),
            dev_packet_path: None,
            dev_receipt_path: None,
            dev_receipt_sha256: None,
        })
        .expect("D7 dev broker response");
        let value: serde_json::Value = serde_json::from_str(&result).expect("response JSON");
        assert_eq!(value["dev_receipt_verified"], true);
        assert_eq!(value["dev_receipt_scope"], "DEV_SELF_SIGNED");
        assert_eq!(value["production_go"], false);
    }
}
