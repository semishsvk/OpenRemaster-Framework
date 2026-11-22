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
const LOCAL_STATUS_CONFIG: &str = include_str!("../local-status-v2-pins.json");

const CONTROL: &str = include_str!("../../tools/studio_dev_control.py");
fn control_scope() -> String {
    let pins: serde_json::Value = serde_json::from_str(CONFIG).expect("compiled DEV JSON");
    // Explicit ordering remains stable if a dependency enables preserve_order.
    fn ordered(value: &serde_json::Value) -> serde_json::Value {
        match value {
            serde_json::Value::Object(map) => {
                let sorted: std::collections::BTreeMap<_, _> = map
                    .iter()
                    .map(|(key, value)| (key.clone(), ordered(value)))
                    .collect();
                serde_json::Value::Object(sorted.into_iter().collect())
            }
            serde_json::Value::Array(items) => {
                serde_json::Value::Array(items.iter().map(ordered).collect())
            }
            _ => value.clone(),
        }
    }
    format!(
        "{:x}",
        Sha256::digest(serde_json::to_vec(&ordered(&pins)).expect("compiled DEV scope"))
    )
}

pub fn capabilities() -> serde_json::Value {
    let check = (|| -> Result<bool, String> {
        let pins: serde_json::Value =
            serde_json::from_str(CONFIG).map_err(|_| "DEV_CONFIG_INVALID")?;
        verify_pins(&pins)?;
        let raw = serde_json::json!({"action":"capabilities","operation_id":"0".repeat(32),"scenario":"build_studio_dev"});
        let value = call_control(&pins, &raw)?;
        if value["production_go"] != false {
            return Err("DEV_CAPABILITY_SCOPE".into());
        }
        Ok(value["healthy"] == true)
    })();
    serde_json::json!({
        "schema":"OpenRemaster.StudioCapabilities.v1", "worker_compiled":true,
        "control_ready":check.is_ok(), "worker_ready":matches!(&check, Ok(true)),
        "recovery_supported":check.is_ok(), "log_archive_supported":check.is_ok(),
        "worker_scope":control_scope(),
        "reason":match check { Ok(true)=>"Pinned HomePC worker is healthy. Builds require a DEV receipt.".to_string(),
            Ok(false)=>"The HomePC worker is stopped or holding. Saved operations can still be inspected and resolved.".to_string(),
            Err(reason)=>format!("DEV control unavailable: {}", reason.chars().take(450).collect::<String>()) },
        "production_go":false
    })
}

fn verify_pins(pins: &serde_json::Value) -> Result<(), String> {
    let root = PathBuf::from(pins["root"].as_str().ok_or("DEV_ROOT_REQUIRED")?);
    if !root.is_absolute() {
        return Err("DEV_ROOT_NOT_ABSOLUTE".into());
    }
    for (path, key) in [
        (
            PathBuf::from(pins["python"].as_str().ok_or("DEV_PYTHON_REQUIRED")?),
            "python_sha256",
        ),
        (root.join("broker.py"), "broker_sha256"),
        (root.join("host.py"), "host_sha256"),
        (root.join("BROKER-PINS.json"), "manifest_sha256"),
        (root.join("WORKER-CONFIG.json"), "worker_config_sha256"),
    ] {
        if hash(&path)? != pins[key].as_str().ok_or("DEV_PIN_REQUIRED")? {
            return Err("DEV_PIN_CHANGED".into());
        }
    }
    Ok(())
}

fn call_control(
    pins: &serde_json::Value,
    request: &serde_json::Value,
) -> Result<serde_json::Value, String> {
    let limit = if request["action"] == "logs" {
        2 * 1024 * 1024
    } else {
        131072
    };
    call_python(
        pins,
        &[
            "-B",
            "-I",
            "-",
            "--config",
            CONFIG,
            "--request",
            &request.to_string(),
        ],
        CONTROL.as_bytes(),
        limit,
        45,
    )
}

// Only the two fixed, pinned read/control adapters below call this bounded I/O
// helper. Renderer input can never select an executable, script or arguments.
fn call_python(
    pins: &serde_json::Value,
    arguments: &[&str],
    script: &[u8],
    limit: u64,
    timeout_seconds: u64,
) -> Result<serde_json::Value, String> {
    let (bytes, success) = call_python_output(pins, arguments, script, limit, timeout_seconds)?;
    let value: serde_json::Value =
        serde_json::from_slice(&bytes).map_err(|_| "DEV_CONTROL_JSON")?;
    if !success {
        return Err(value["error"].as_str().unwrap_or("DEV_CONTROL_HOLD")
            .chars().take(2048).collect());
    }
    Ok(value)
}

// Exact bounded byte transport shared by fixed source-pinned adapters only.
pub(super) fn call_python_output(
    pins: &serde_json::Value,
    arguments: &[&str],
    input: &[u8],
    limit: u64,
    timeout_seconds: u64,
) -> Result<(Vec<u8>, bool), String> {
    use std::io::Write;
    use std::sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    };
    let mut child = Command::new(pins["python"].as_str().ok_or("DEV_PYTHON_REQUIRED")?)
        .args(arguments)
        .current_dir(pins["root"].as_str().ok_or("DEV_ROOT_REQUIRED")?)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .creation_flags(0x08000000)
        .spawn()
        .map_err(|_| "DEV_CONTROL_START_FAILED")?;
    let overflow = Arc::new(AtomicBool::new(false));
    fn reader<R: Read + Send + 'static>(
        stream: R,
        flag: Arc<AtomicBool>,
        limit: u64,
    ) -> thread::JoinHandle<std::io::Result<Vec<u8>>> {
        thread::spawn(move || {
            let mut bytes = Vec::new();
            stream.take(limit + 1).read_to_end(&mut bytes)?;
            if bytes.len() as u64 > limit {
                flag.store(true, Ordering::SeqCst);
            }
            Ok(bytes)
        })
    }
    let stdout = reader(
        child.stdout.take().ok_or("DEV_CONTROL_STDOUT")?,
        overflow.clone(),
        limit,
    );
    let stderr = reader(
        child.stderr.take().ok_or("DEV_CONTROL_STDERR")?,
        overflow.clone(),
        limit,
    );
    if child
        .stdin
        .take()
        .ok_or("DEV_CONTROL_STDIN")?
        .write_all(input)
        .is_err()
    {
        let _ = child.kill();
        let _ = child.wait();
        return Err("DEV_CONTROL_INPUT_FAILED".into());
    }
    let started = Instant::now();
    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break status,
            Ok(None) => {}
            Err(_) => {
                let _ = child.kill();
                let _ = child.wait();
                return Err("DEV_CONTROL_WAIT_FAILED".into());
            }
        }
        if started.elapsed() > Duration::from_secs(timeout_seconds)
            || overflow.load(Ordering::SeqCst)
        {
            let _ = child.kill();
            let _ = child.wait();
            return Err("DEV_CONTROL_BOUND_HOLD".into());
        }
        thread::sleep(Duration::from_millis(20));
    };
    let bytes = stdout
        .join()
        .map_err(|_| "DEV_CONTROL_READER")?
        .map_err(|_| "DEV_CONTROL_READ")?;
    let _ = stderr
        .join()
        .map_err(|_| "DEV_CONTROL_READER")?
        .map_err(|_| "DEV_CONTROL_READ")?;
    if overflow.load(Ordering::SeqCst) {
        return Err("DEV_CONTROL_RESPONSE_SIZE".into());
    }
    Ok((bytes, status.success()))
}

fn validate_local_status(value: serde_json::Value, now: f64) -> Result<serde_json::Value, String> {
    let captured = value["captured_epoch"]
        .as_f64()
        .ok_or("LOCAL_STATUS_CAPTURE_REQUIRED")?;
    if !matches!(
        value["schema"].as_str(),
        Some("OpenRemaster.LocalStudioStatus.v1" | "OpenRemaster.LocalStudioStatus.v2")
    ) || value["mode"] != "LOCAL_DEV"
        || value["source"] != "LOCAL_NATIVE_READONLY"
        || value["read_only"] != true
        || value["production_go"] != false
        || value["azure_required"] != false
        || value["witness_required"] != false
        || !captured.is_finite()
        || captured > now + 2.0
        || now - captured > 10.0
        || value["jobs"]
            .as_array()
            .map_or(true, |jobs| jobs.len() > 12)
        || !value["host"].is_object()
        || !value["counts"].is_object()
    {
        return Err("LOCAL_STATUS_RESPONSE_SCOPE".into());
    }
    Ok(value)
}

pub fn local_status() -> Result<serde_json::Value, String> {
    use std::os::windows::fs::MetadataExt;
    let pins: serde_json::Value =
        serde_json::from_str(LOCAL_STATUS_CONFIG).map_err(|_| "DEV_CONFIG_INVALID")?;
    if pins["schema"] != "OpenRemaster.LocalStatusNativePins.v2"
        || pins["contract_id"] != "UNIFIED-DEV-20261119-01"
        || pins["reader"] != "local_status_v2.py"
        || pins["validator"] != "transactional_queue.py"
        || pins["response_schema"] != "OpenRemaster.LocalStudioStatus.v2"
        || pins["native_arguments"] != serde_json::json!([])
    {
        return Err("LOCAL_STATUS_NOT_COMMISSIONED".into());
    }
    let root = PathBuf::from(pins["root"].as_str().ok_or("DEV_ROOT_REQUIRED")?);
    let python = PathBuf::from(pins["python"].as_str().ok_or("DEV_PYTHON_REQUIRED")?);
    if !root.is_absolute() || !python.is_absolute() {
        return Err("LOCAL_STATUS_PATH_NOT_ABSOLUTE".into());
    }
    let reader = root.join("local_status_v2.py");
    let validator = root.join("transactional_queue.py");
    for ancestor in reader
        .ancestors()
        .chain(validator.ancestors())
        .chain(python.ancestors())
    {
        if fs::symlink_metadata(ancestor)
            .map_err(|_| "LOCAL_STATUS_PATH_UNAVAILABLE")?
            .file_attributes()
            & 0x400
            != 0
        {
            return Err("LOCAL_STATUS_REPARSE_DENIED".into());
        }
    }
    if hash(&python)?
        != pins["python_sha256"]
            .as_str()
            .ok_or("LOCAL_STATUS_PIN_REQUIRED")?
        || hash(&validator)?
            != pins["validator_sha256"]
                .as_str()
                .ok_or("LOCAL_STATUS_PIN_REQUIRED")?
    {
        return Err("LOCAL_STATUS_DEPENDENCY_CHANGED".into());
    }
    let mut source = Vec::new();
    fs::File::open(&reader)
        .map_err(|_| "LOCAL_STATUS_READER_UNAVAILABLE")?
        .take(65537)
        .read_to_end(&mut source)
        .map_err(|_| "LOCAL_STATUS_READER_READ")?;
    if source.len() > 65536
        || format!("{:x}", Sha256::digest(&source))
            != pins["reader_sha256"]
                .as_str()
                .ok_or("LOCAL_STATUS_PIN_REQUIRED")?
    {
        return Err("LOCAL_STATUS_READER_CHANGED".into());
    }
    // Execute exactly the bytes just hashed. __file__ keeps the approved reader's
    // fixed root; reopening a mutable script after verification is avoided.
    let encoded = source
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect::<String>();
    let input = format!(
        "__file__ = {}\nexec(compile(bytes.fromhex('{}'), __file__, 'exec'))\n",
        serde_json::to_string(&reader.to_string_lossy()).map_err(|_| "LOCAL_STATUS_PATH")?,
        encoded
    )
    .into_bytes();
    let value = call_python(&pins, &["-B", "-I", "-"], &input, 65536, 8)?;
    // No fallback to the historical v1 reader when a v2 read is unavailable.
    if value["schema"] != pins["response_schema"] {
        return Err("LOCAL_STATUS_UNSUPPORTED_SCHEMA".into());
    }
    validate_local_status(
        value,
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_err(|_| "LOCAL_STATUS_CLOCK")?
            .as_secs_f64(),
    )
}

#[derive(Deserialize, Clone)]
#[serde(deny_unknown_fields)]
pub struct RecoveryRequest {
    expected_evidence_sha256: String,
    #[serde(default)]
    reason: Option<String>,
    #[serde(default)]
    acknowledge: Option<bool>,
}
#[derive(Deserialize, Clone)]
#[serde(deny_unknown_fields)]
pub struct LogRequest {
    source: String,
    name: String,
    offset: u64,
    limit: u64,
    #[serde(default)]
    manifest_sha256: Option<String>,
}
#[derive(Deserialize, Clone)]
#[serde(deny_unknown_fields)]
pub struct DevRequest {
    action: String,
    operation_id: String,
    scenario: String,
    #[serde(default)]
    attempt_id: Option<String>,
    #[serde(default)]
    log: Option<LogRequest>,
    #[serde(default)]
    recovery: Option<RecoveryRequest>,
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
    if ![
        "submit",
        "status",
        "archive",
        "resolve",
        "logs",
        "export",
        "prove_not_admitted",
    ]
    .contains(&request.action.as_str())
        || request.scenario != "build_studio_dev"
        || request.operation_id.len() != 32
        || !request
            .operation_id
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Err("DEV_REQUEST_DENIED".into());
    }
    let mut raw = serde_json::json!({"action":request.action,"operation_id":request.operation_id,"scenario":request.scenario});
    if let Some(attempt) = &request.attempt_id {
        if !["submit", "resolve", "prove_not_admitted"].contains(&request.action.as_str())
            || attempt.len() != 32
            || !attempt
                .bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        {
            return Err("DEV_ATTEMPT_SCOPE".into());
        }
        raw["attempt_id"] = serde_json::json!(attempt);
    }
    if request.action == "prove_not_admitted" && request.attempt_id.is_none() {
        return Err("DEV_ATTEMPT_SCOPE".into());
    }
    if ["archive", "resolve", "logs", "export", "prove_not_admitted"]
        .contains(&request.action.as_str())
    {
        let recovery = request
            .recovery
            .as_ref()
            .ok_or("DEV_RECOVERY_DETAILS_REQUIRED")?;
        if recovery.expected_evidence_sha256.len() != 64
            || !recovery
                .expected_evidence_sha256
                .bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        {
            return Err("DEV_RECOVERY_EVIDENCE_REQUIRED".into());
        }
        raw["expected_evidence_sha256"] = serde_json::json!(recovery.expected_evidence_sha256);
        if request.action == "resolve"
            && (recovery.acknowledge != Some(true)
                || recovery
                    .reason
                    .as_ref()
                    .map(|s| s.trim().len() < 10 || s.len() > 1024)
                    .unwrap_or(true))
        {
            return Err("DEV_EXPLICIT_ACKNOWLEDGMENT_REQUIRED".into());
        }
        raw["reason"] = serde_json::json!(recovery.reason);
        raw["acknowledge"] = serde_json::json!(recovery.acknowledge);
    } else if request.recovery.is_some() {
        return Err("DEV_UNEXPECTED_RECOVERY_DETAILS".into());
    }
    if request.action == "logs" {
        let log = request.log.as_ref().ok_or("DEV_LOG_DETAILS_REQUIRED")?;
        if !["live", "archive", "bundle"].contains(&log.source.as_str())
            || !(if log.source == "bundle" {
                log.name == "diagnostics.zip"
            } else {
                ["stdout.log", "stderr.log"].contains(&log.name.as_str())
            })
            || log.limit == 0
            || log.limit > 1024 * 1024
            || log.offset > 64 * 1024 * 1024 + 131072
        {
            return Err("DEV_LOG_PAGE_SCOPE".into());
        }
        raw["source"] = serde_json::json!(log.source);
        raw["name"] = serde_json::json!(log.name);
        raw["offset"] = serde_json::json!(log.offset);
        raw["limit"] = serde_json::json!(log.limit);
        if let Some(manifest) = &log.manifest_sha256 {
            raw["manifest_sha256"] = serde_json::json!(manifest);
        }
    } else if request.log.is_some() {
        return Err("DEV_UNEXPECTED_LOG_DETAILS".into());
    }
    let pins: serde_json::Value = serde_json::from_str(CONFIG).map_err(|_| "DEV_CONFIG_INVALID")?;
    verify_pins(&pins)?;
    let root = PathBuf::from(pins["root"].as_str().ok_or("DEV_ROOT_REQUIRED")?);
    let python = PathBuf::from(pins["python"].as_str().ok_or("DEV_PYTHON_REQUIRED")?);
    if request.action == "submit" {
        if let Some(reason) = crate::dev_preflight::submission_blocker() {
            if request.attempt_id.is_none() {
                return Err(reason.into());
            }
            // Ask the pinned client to prove absence under the original locks.
            // Failure to obtain that proof leaves the saved UI ID on HOLD.
            raw["action"] = serde_json::json!("reject");
            raw["reason"] = serde_json::json!(reason);
            let mut rejected = call_control(&pins, &raw)?;
            if rejected["schema"] != "OpenRemaster.DevWorkflowResult.v2"
                || rejected["operation_id"] != request.operation_id
                || rejected["control_scope"] != control_scope()
                || rejected["control_verified"] != true
                || rejected["production_go"] != false
                || rejected["independent_authority"] != false
                || rejected["state"] != "DENIED"
                || rejected["launch_count"] != 0
                || rejected["not_admitted"]["attempt_id"].as_str() != request.attempt_id.as_deref()
            {
                return Err("DEV_REJECTION_SCOPE".into());
            }
            rejected["dev_receipt_verified"] = serde_json::json!(false);
            return Ok(rejected.to_string());
        }
    }
    // Only execution admission issues/verifies a DEV receipt. Status/recovery do not.
    let receipt = if request.action == "submit" {
        let admitted = if request.dev_receipt_path.is_none() && request.dev_receipt_sha256.is_none()
        {
            issue_ephemeral_receipt(&root, &python, &pins, &request)?
        } else {
            request.clone()
        };
        Some(verify_dev_receipt(&root, &python, &pins, &admitted)?)
    } else {
        if request.dev_packet_path.is_some()
            || request.dev_receipt_path.is_some()
            || request.dev_receipt_sha256.is_some()
        {
            return Err("DEV_OBSERVATION_RECEIPT_NOT_ACCEPTED".into());
        }
        None
    };
    if let Some(ref admitted_sha) = receipt {
        raw["dev_receipt_sha256"] = serde_json::json!(admitted_sha);
    }
    let mut value = call_control(&pins, &raw)?;
    if request.action == "prove_not_admitted"
        && (value["state"] != "DENIED"
            || value["launch_count"] != 0
            || value["not_admitted"]["attempt_id"].as_str() != request.attempt_id.as_deref())
    {
        return Err("DEV_REJECTION_SCOPE".into());
    }
    if ["logs", "export"].contains(&request.action.as_str()) {
        let schema = if request.action == "logs" {
            "OpenRemaster.DevLogPage.v1"
        } else {
            "OpenRemaster.DevLogExport.v1"
        };
        if value["schema"] != schema
            || value["operation_id"] != request.operation_id
            || value["scope"] != control_scope()
            || value["production_go"] != false
        {
            return Err("DEV_LOG_RESPONSE_SCOPE".into());
        }
        return Ok(value.to_string());
    }
    if value["schema"] != "OpenRemaster.DevWorkflowResult.v2"
        || value["operation_id"] != request.operation_id
        || value["production_go"] != false
        || value["independent_authority"] != false
        || value["control_verified"] != true
        || value["control_scope"] != control_scope()
    {
        return Err("DEV_CONTROL_RESPONSE_SCOPE".into());
    }
    value["dev_receipt_verified"] = serde_json::json!(receipt.is_some());
    if let Some(receipt) = receipt {
        value["dev_receipt_sha256"] = serde_json::json!(receipt);
    }
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
    fn portable_local_status_rejects_stale_or_production_claims() {
        let valid = serde_json::json!({"schema":"OpenRemaster.LocalStudioStatus.v1","captured_epoch":1000.0,
            "mode":"LOCAL_DEV","source":"LOCAL_NATIVE_READONLY","read_only":true,"production_go":false,
            "azure_required":false,"witness_required":false,"host":{},"counts":{},"jobs":[]});
        assert!(validate_local_status(valid.clone(), 1000.0).is_ok());
        assert!(validate_local_status(valid.clone(), 1011.0).is_err());
        assert!(validate_local_status(valid.clone(), 997.0).is_err());
        let mut promoted = valid;
        promoted["production_go"] = serde_json::json!(true);
        assert!(validate_local_status(promoted, 1000.0).is_err());
    }
    #[test]
    fn portable_log_paths_are_rejected_before_worker_access() {
        let request: DevRequest = serde_json::from_value(serde_json::json!({
            "action":"logs","operation_id":"a".repeat(32),"scenario":"build_studio_dev",
            "recovery":{"expected_evidence_sha256":"b".repeat(64)},
            "log":{"source":"archive","name":"../ledger.sqlite","offset":0,"limit":65536}
        }))
        .unwrap();
        assert_eq!(execute(request).unwrap_err(), "DEV_LOG_PAGE_SCOPE");
    }
    #[test]
    fn portable_rejects_recovery_without_current_evidence() {
        let request = DevRequest {
            action: "resolve".into(),
            operation_id: "a".repeat(32),
            scenario: "build_studio_dev".into(),
            attempt_id: None,
            log: None,
            recovery: None,
            dev_packet_path: None,
            dev_receipt_path: None,
            dev_receipt_sha256: None,
        };
        assert_eq!(
            execute(request.clone()).unwrap_err(),
            "DEV_RECOVERY_DETAILS_REQUIRED"
        );
        let mut invalid = request.clone();
        invalid.recovery = Some(RecoveryRequest {
            expected_evidence_sha256: "../escape".into(),
            reason: None,
            acknowledge: None,
        });
        assert_eq!(
            execute(invalid).unwrap_err(),
            "DEV_RECOVERY_EVIDENCE_REQUIRED"
        );
        let mut unconfirmed = request;
        unconfirmed.recovery = Some(RecoveryRequest {
            expected_evidence_sha256: "b".repeat(64),
            reason: Some("Diagnostic note provided".into()),
            acknowledge: Some(false),
        });
        assert_eq!(
            execute(unconfirmed).unwrap_err(),
            "DEV_EXPLICIT_ACKNOWLEDGMENT_REQUIRED"
        );
    }
    #[test]
    fn portable_scope_matches_python_canonical_config() {
        assert_eq!(
            control_scope(),
            "c5f58f85ae31f4f9a674ae24a9c3ca9d08b18a01fcee35cb81064c828440d60e"
        );
    }
    #[test]
    fn rejects_request_before_spawn() {
        assert!(execute(DevRequest {
            action: "submit".into(),
            operation_id: "../escape".into(),
            scenario: "normal".into(),
            attempt_id: None,
            log: None,
            recovery: None,
            dev_packet_path: None,
            dev_receipt_path: None,
            dev_receipt_sha256: None
        })
        .is_err());
        assert!(execute(DevRequest {
            action: "submit".into(),
            operation_id: "a".repeat(32),
            scenario: "shell".into(),
            attempt_id: None,
            log: None,
            recovery: None,
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
            attempt_id: None,
            log: None,
            recovery: None,
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
            attempt_id: None,
            log: None,
            recovery: None,
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
            attempt_id: None,
            log: None,
            recovery: None,
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
            attempt_id: None,
            log: None,
            recovery: None,
            dev_packet_path: None,
            dev_receipt_path: Some(tampered.display().to_string()),
            dev_receipt_sha256: Some(hash(&tampered).expect("tampered hash")),
        };
        let result = verify_dev_receipt(&root, &python, &pins, &request);
        let _ = fs::remove_file(&tampered);
        assert_eq!(result.unwrap_err(), "DEV_RECEIPT_SIGNATURE_INVALID");
    }

    #[test]
    #[ignore = "bounded commissioned LOCAL_DEV read-only native smoke; never submits a build"]
    fn runtime_smoke_returns_dev_scope() {
        let value = local_status().expect("commissioned read-only HomePC status");
        assert_eq!(value["schema"], "OpenRemaster.LocalStudioStatus.v2");
        assert_eq!(value["read_only"], true);
        assert!(value["host"]["healthy"].is_boolean());
        assert_eq!(value["production_go"], false);
    }
}
