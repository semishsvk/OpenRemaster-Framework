# Deterministic Replay Contract

Phase 1 defines a runtime-neutral replay/evidence contract. It does not modify or instrument project runtimes.

A replay identity binds:
- project ID and exact source revision,
- runtime ID/version,
- fixed simulation tick rate,
- deterministic seed,
- canonical per-tick actions and axes.

A runtime adapter may later emit:
- ordered semantic events,
- world-state checkpoint hashes.

Two executions of the same replay are deterministic only when replay identity, event trace and checkpoint sequence match exactly.

This contract intentionally avoids screenshots or video as the primary proof. Visual/audio artifacts may be attached later, but semantic events and world-state hashes provide machine-verifiable evidence.

OpenAzrael integration must remain a separately accepted adapter/runtime-instrumentation step. OpenCadaver can implement the same contract when its runtime reaches that stage.
