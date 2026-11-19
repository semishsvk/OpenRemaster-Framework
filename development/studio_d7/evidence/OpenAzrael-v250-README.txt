OpenAzrael Candidate v250
=========================

High-quality gameplay / presentation / diagnostic validation build of the Azrael's Tear demo reconstruction.

Controls
--------
WASD       Move
E          Interact
F8         Toggle ORIGINAL / UPSCALED 4X textures
M          Map
Arrow keys Legacy movement / inventory scrolling where applicable

Localization
------------
English and experimental Slovak localization are included.

Graphics
--------
ORIGINAL is the fidelity baseline.
UPSCALED 4X uses deterministic nearest-neighbour 4x pixel-preserving texture variants. It does not invent new texture detail.

Validated candidate baseline
----------------------------
Full demo 34/34 PASS
Inventory/HUD 40/40 PASS
Object lifecycle 85/85 PASS
Cursor/interactions 169/169 PASS
Save/load 37/37 PASS
Niamh 29/29 PASS
Eugene 9/9 PASS
R1 parchment 7/7 PASS
Localization 89/89 EN/SK; 12/12 PASS
Graphics mode 12/12 PASS
EN/SK x Original/Upscaled matrix 8/8 PASS
Physical PPPV transitions 109/109 PASS
Clean install / startup PASS
Bug-report diagnostic context 4/4 PASS

Known deferred fidelity gaps
----------------------------
- Original MOV cinematics / exact decode and timing.
- Exact original-runtime SERVICE/HUD activation timing.
- Final paired original-runtime visual FidelityBundle.

This candidate must therefore not be described as a 100% fidelity/final release.
