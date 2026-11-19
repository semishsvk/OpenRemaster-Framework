#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
mod dev_preflight;
#[cfg(feature = "dev-worker")]
mod dev_worker;

#[tauri::command]
async fn studio_capabilities() -> Result<serde_json::Value, String> {
    #[cfg(feature = "dev-worker")]
    return tauri::async_runtime::spawn_blocking(|| {
        dev_preflight::attach(dev_worker::capabilities())
    })
    .await
    .map_err(|_| "DEV_CAPABILITIES_PANIC".to_string());
    #[cfg(not(feature = "dev-worker"))]
    Ok(dev_preflight::attach(serde_json::json!({
        "schema": "OpenRemaster.StudioCapabilities.v1",
        "worker_compiled": false, "worker_ready": false,
        "worker_scope": null, "reason": "This portable build contains the Studio UI. DEV worker support requires a commissioned HomePC build.",
        "production_go": false
    })))
}

#[tauri::command]
fn studio_open_release(url: String) -> Result<(), String> {
    let parsed = tauri::Url::parse(&url).map_err(|_| "Invalid release URL")?;
    let prefix = "/semishsvk/OpenRemaster-Framework/";
    if parsed.scheme() != "https"
        || parsed.host_str() != Some("github.com")
        || parsed.port().is_some()
        || !parsed.username().is_empty()
        || parsed.password().is_some()
        || parsed.query().is_some()
        || parsed.fragment().is_some()
        || !parsed
            .path()
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"._/-".contains(&b))
        || !(parsed.path() == format!("{prefix}releases")
            || ["releases/tag/", "releases/download/", "actions/runs/"]
                .iter()
                .any(|suffix| parsed.path().starts_with(&format!("{prefix}{suffix}"))))
    {
        return Err("Only this project's GitHub release and CI links are allowed".into());
    }
    let explorer = std::path::PathBuf::from(
        std::env::var_os("SystemRoot").ok_or("Windows directory unavailable")?,
    )
    .join("explorer.exe");
    std::process::Command::new(explorer)
        .arg(parsed.as_str())
        .spawn()
        .map_err(|_| "Could not open the default browser")?;
    Ok(())
}

fn main() {
    let builder = tauri::Builder::default();
    #[cfg(not(feature = "dev-worker"))]
    let builder = builder.invoke_handler(tauri::generate_handler![
        studio_capabilities,
        studio_open_release
    ]);
    #[cfg(feature = "dev-worker")]
    let builder = builder.invoke_handler(tauri::generate_handler![
        studio_capabilities,
        studio_open_release,
        dev_worker::dev_worker_call
    ]);
    builder
        .run(tauri::generate_context!())
        .expect("Studio failed to start");
}
