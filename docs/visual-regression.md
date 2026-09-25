# Visual Regression Contract

Visual evidence is bound to a deterministic capture contract rather than to a filename.

The contract includes exact project source revision, scene/room ID, fixed camera identity and transform, field of view, render dimensions, lighting profile, renderer identity/version, and world-state digest.

The image artifact stores the capture-contract digest and the SHA-256 of the rendered bytes.

Exact digest equality is the Phase 1 proof primitive. If two images share the same capture contract but have different image digests, the result is a regression candidate for a later perceptual/pixel-diff stage.

Different lighting profiles are intentionally different contracts. This directly supports separate original-1996 and neutral OpenAzrael baselines without treating expected lighting differences as regressions.

No renderer or Godot integration is performed by Phase 1.
