# OpenAzrael build review

Open **Projects → OpenAzrael build review** in Studio. The panel shows archived results for `candidate-v205-iter2` and `OpenAzrael-v250`, both `README_HOLD` observations, six comparisons and the original and remaster captures of the R1 corridor. The R1 capture remains at `FIDELITY HOLD` because camera position and HUD phase were only partially synchronized.

Run `npm test` and `npm run build` from this directory. This integration uses the existing Projects route and captured assets.

**Settings → Studio build** shows the desktop version, the source commit when building from a clean Git checkout, and the UTC time at which the frontend was built. A source export without Git metadata displays `Unavailable` for the commit.

The Studio review workflow verifies English copy, all three Release & Trust stages, the build identity and both OpenAzrael comparisons in offline Chromium at desktop and mobile widths.
