# OpenRemaster Fidelity Gates v1 — 2026-10-09

Status: **APPROVED / IMPLEMENTED / SOFTWARE-TESTED / PRODUCTION-HOLD**.

Versioned, engine-neutral sidecar. No edits to Phase 1 frozen baseline, no edits
to canonical source game data, no changes to active ORCH-K003 validator or worker
routing. The five approved contracts are implemented using Python standard library.

## Gate order

1. OracleAlignmentContract.v1: same source corpus identity, canonical scene,
   scenario, replay, capture point, input trace, camera normalization/projection,
   yaw/pitch/FOV, viewport and ticks. Actual original and candidate capture bytes
   plus alignment-policy evidence are independently reopened and SHA-256 checked.
2. ComparisonAdmissibilityGuard.v1: ADMISSIBLE only after gate 1 is ALIGNED.
   Wrong scene/camera/tick => ALIGNMENT_BLOCKED, missing/bad evidence =>
   INSUFFICIENT_EVIDENCE. Neither is a pixel fidelity FAIL.
3. CausalFidelityDiff.v1: separate camera, geometry, UV, palette, objects,
   animation, HUD, audio, timing, input, state, lighting and transparency.
   A possible mechanism is only HYPOTHESIS until a controlled repeated
   intervention supports or refutes it. Never generates fidelity PASS.
4. ResourceResolutionContract.v1: canonical case-insensitive paths,
   game-specific explicit layer order, duplicate/conflict detection, source
   hashes, independent precedence evidence. A source-only ordering hypothesis
   is STRUCTURAL_ONLY, never a verified gameplay override.
5. SemanticPopulationGuard.v1: definitions != references != materialized
   runtime instances. Enforces instance parent integrity, no cycles, active
   population bands and per-game evidence. Valid structural records are not
   proof of actual game-world population.

## Status hierarchy

- ALIGNED / ADMISSIBLE only means paired comparison is allowed.
- ALIGNMENT_BLOCKED prohibits fidelity scoring; it is not FIDELITY_FAIL.
- INSUFFICIENT_EVIDENCE and STRUCTURAL_ONLY cannot promote gameplay.
- SUPPORTED_CAUSE does not establish root-cause certainty.
- ELIGIBLE_FOR_EXTERNAL_ACCEPTANCE never means FIDELITY_VERIFIED.
- Final fidelity acceptance stays in ORCH-K003's independent validator and
  game-specific replay/capture contracts. User assertions and worker self-
  reports cannot bypass this.

## CLI

Use the versioned directory and absolute paths to canonical capture outputs,
not to immutable source-data directories.

    python gate_cli.py alignment alignment_bundle.json --original-root <dir> --reconstruction-root <dir> --policy-root <dir>
    python gate_cli.py resources layer_manifest.json --evidence-root <dir>
    python gate_cli.py population population_manifest.json --evidence-root <dir>

Returns exit 0 only for contract-admissible results, exit 2 for blocked/held
or insufficient evidence, and exit 3 on contract or input errors.
All results print machine-readable JSON. Optional --output writes results,
but never to canonical source trees.

## ORCH-K003 integration (opt-in, not yet active in native control flow)

The existing orchestrator/control-plane/validator.py is kept immutable here.
For a future owner-controlled rollout, import orch_adapter.gated_validate and
wrap the current independent validator. Jobs with execution.kind=fidelity_runtime
then require validation.oracle_alignment with the SHA-256 of a manifest
in the same result directory, plus trusted capture/policy roots. Without
them the wrapped validator fails closed. Ordinary godot_runtime jobs remain
unchanged unless validation.require_scene_alignment=true is set.

The single-writer/integration admission gate is not met just by shipping
this module. Do not redirect live ORCH-K003 without an agreed writer lease,
reproducible restore checkpoint, exact-HEAD tests and native E2E canary.

## Actual game regressions included

- OpenZork R27 actual checkpoint: scene/view mismatch => no pixel score.
- OpenMDK1 renderer checkpoint v3: structural geometry/material/palette
  PASS cannot imply visual fidelity PASS.
- OpenUltima9 NONFIXED pages: physical != reachable; no page-count shortcut
  for runtime entity multiplicity.
- Fallout 2 master.dat/patch000.dat: actual read-only DAT2 indexes,
  overlapping paths and twelve independently decompressed asset pairs.
  Runtime precedence explicitly remains a hypothesis, so STRUCTURAL_ONLY.

## Safety / ownership

- Stage and code copies are outside F:\Remaster Framework\source.
- Do not use RDC stream as source of fidelity images.
- No network, background worker dispatch, GUI action, game launch,
  production stop, lease stealing or shared source-file write in this package.
- Only append a new versioned module under orchestrator once tests and hashes pass.
- Phase 1 frozen acceptance remains untouched.
