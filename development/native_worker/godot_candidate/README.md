# Isolated Godot DEV source candidate

This review overlay adds a named Godot export adapter to the existing DEV broker and queue. It does not start another worker or replace the preserved worker sources beside this directory.

The adapter pins recipes, source and tool inputs, copies into fresh operation scopes, validates named outputs and rechecks owner/resource admission through the existing callback. That callback remains HOLD until connected to an independently verified existing authority. Ledger ACK/result/commit and saved-result replay retain operation and recipe bindings. Recipe reads are bounded before parsing.

No host configuration, real-project manifests, dependency cache, credentials, signing keys or operational receipts are included. Self-issued DEV custody is not production signing or independent release authority. Existing K003/owner/resource admission, single-writer, GAME/LIGHT and the three-heavy-slot limit remain required before real execution.

Local Windows sandbox qualification: **116 tests PASS**. Process, engine and authority outcomes are explicit test doubles; no real export or native compilation. CI was not run. This is source review, not activation or acceptance.

The tests require the existing qualified Python/pytest dependencies and project writer guard. They cover only this generic overlay; no historical launchers or original game corpus belong in test discovery. The runtime/config pin closure and both compiled consumers still require an admitted isolated integration before commissioning.

Production activation, signing, publishing, promotion, fallback and automatic retry are not granted by this source candidate.
