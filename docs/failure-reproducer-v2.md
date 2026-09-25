# Failure Reproducer v2

A long deterministic replay can be reduced to a smaller reproduction window when a failure tick is known.

The reducer selects the nearest world-state checkpoint at or before the failure and keeps only input frames from that checkpoint through the failure tick. Input ticks are rebased to zero while project revision, runtime identity, seed and the parent replay digest remain bound.

The checkpoint state digest is mandatory. This prevents a short replay from pretending to be independently reproducible when it actually depends on world state created earlier in the full playthrough.

Phase 1 performs deterministic slicing only. It does not synthesize missing world state, execute the game, or claim that the reduced slice reproduces the failure until a runtime adapter executes and verifies it.
