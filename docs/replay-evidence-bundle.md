# Replay Evidence Bundle

A replay evidence bundle is the portable, deterministic proof unit for a runtime observation or failure.

It binds:
- exact replay contract,
- runtime semantic event trace,
- world-state checkpoint sequence,
- optional artifact references such as runtime logs, screenshots, audio captures or engine reports.

Artifacts are represented by SHA-256 digest and role. Their locator is descriptive only and is not used as proof of content.

The trace must reference the exact replay digest. The complete bundle itself has a canonical SHA-256 identity.

A failure descriptor can then bind project, source SHA, category, room/subject, summary and replay-bundle digest into a stable failure ID.

This is designed for future floor-collision, stairs, portal, trigger and puzzle reproductions without requiring the framework to mutate the game project.
