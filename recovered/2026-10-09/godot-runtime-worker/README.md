# OpenRemaster GodotRuntimeWorker

Canonical HomePC runtime-validation worker for OpenRemaster projects.

Pipeline: checkpoint/rehydrate -> clean import -> Godot execution -> deterministic replay -> local capture -> assertions/diff -> evidence -> artifact bridge.

Rules:
- Godot source binaries come from F:\Remaster Framework\source\Godot.
- Remote Desktop Commander may orchestrate execution, but its image/video stream is never fidelity authority.
- Fidelity captures must be written locally by the runtime/capture process.
- Each job produces a machine-readable result and execution-environment fingerprint.
- Project source/corpus remains read-only unless the project contract explicitly provides a generated workspace.
