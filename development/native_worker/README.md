# Preserved unsigned DEV worker source

Source from the existing unified DEV worker revision 05. The recorded DEV operation built a Studio EXE, but this source export does not contain the commissioned host runtime, dependency cache, embedded absolute configuration or input snapshots.

`worker-native/src/main.rs` deliberately requires a separately provisioned `WORKER-CONFIG.json` and exact pins before startup. The broker retains local-only ACK/commit semantics and fixed `build_studio_dev` allowlisting. Self-issued protocol custody is development evidence only; it is unrelated to production Authenticode signing or independent release authority.

Do not run the bootstrap scripts in a shared workspace or delete source-pin checks to force startup. Existing K003/Owner/Governor admission and a fresh project-scoped configuration remain required. No scheduled task or active worker is changed by this source preservation.
