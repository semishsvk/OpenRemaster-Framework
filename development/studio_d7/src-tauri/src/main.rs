#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
#[cfg(feature = "dev-worker")]
mod dev_worker;
fn main() {
    let builder = tauri::Builder::default();
    #[cfg(feature = "dev-worker")]
    let builder = builder.invoke_handler(tauri::generate_handler![dev_worker::dev_worker_call]);
    builder
        .run(tauri::generate_context!())
        .expect("Studio failed to start");
}
