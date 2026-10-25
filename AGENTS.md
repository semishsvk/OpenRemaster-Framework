# OpenRemaster consolidated development candidate

Single coordination context: OpenRemaster — Master Development, thread `01a1734c-aca7-7d03-8a77-1168008db312`.

Read `docs/master-development/COORDINATION.md` and `MASTER_DEVELOPMENT_STATE.json` before implementation. Preserve existing Core, historical code vault, R01–R14 priorities and source-specific acceptance boundaries. The `development/` tree is an isolated integration candidate, not a production or canonical game baseline.

Reuse K003, owner admission, writer leases, Resource Governor, ORION proposals and evidence stores. Do not add a competing execution scheduler. One writer per project; at most three heavy tasks; original corpora read-only; GAME/LIGHT and shared HomePC GUI constraints apply. An idle thread is not lease release.

Remain inside the sandbox. Do not request elevated privileges, disable sandboxing or change system security settings. A Windows 1314 symlink setup failure is an explicit environment SKIP, never a security PASS. Keep the real symlink rejection test and separately label simulated branch evidence.

DEVELOPMENT workers have no production signing or publication authority. Missing or contradictory trust evidence means HOLD/REJECT. Production activation requires independent validation and separate explicit user approval.

Run `python -B scripts/development_acceptance.py --out <fresh-dir>` for portable source/synthetic tests and the existing Core pytest suite with its pinned test dependencies. Never execute historical recovered launchers as part of generic test discovery. No original-game runtime, native GUI or production trust is implied by source tests.
