"""EXPERIMENTAL native ZORKDOS New Game input guard (not a fidelity oracle).
Only permit guest mouse click after a local WGC image of the exact owned HWND
matches an independently recovered original game cursor at New Game.
Uses conservative positive/negative original-runtime fixtures, NEVER host input.
"""
from pathlib import Path
import hashlib
import numpy as np
from PIL import Image
from fidelity_runtime_isolation_v1 import IsolationError

ROOT=Path(__file__).resolve().parents[2]
TEMPLATE=ROOT/"work"/"OpenZork"/"runtime"/"assets"/"cursors"/"00idlea.png"
EXPECTED_SHA="cc97b9ba0a3216bfc3e85fef076425f2cdcf1b1d77cd16fbf1675b3110ea3923"
# Calibrated only on original DOSBox-X (644x557), NOT other engine/windows:
ALLOWED_X=(305,333)
ALLOWED_Y=(408,432)
MAX_RMSE=70.0

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _valid_conv(a,kernel):
    h,w=a.shape
    kh,kw=kernel.shape
    shape=(h+kh-1,w+kw-1)
    result=np.fft.irfft2(np.fft.rfft2(a,s=shape) *
                         np.fft.rfft2(kernel[::-1,::-1],s=shape),s=shape)
    return result[kh-1:h,kw-1:w]

def evaluate_original_newgame_cursor(image_file):
    img=Path(image_file).resolve(strict=True)
    if not TEMPLATE.is_file() or sha(TEMPLATE)!=EXPECTED_SHA:
        raise IsolationError("NATIVE_CURSOR_SOURCE_HASH_UNEXPECTED")
    with Image.open(img) as im:
        if im.size!=(644,557):
            raise IsolationError("NATIVE_CURSOR_WGC_GEOMETRY_UNSUPPORTED",
                                 {"got":im.size,"expected":[644,557]})
        target=np.asarray(im.convert("RGB"),dtype=np.float64)
    with Image.open(TEMPLATE) as im:
        rgba=np.asarray(im.convert("RGBA"),dtype=np.float64)
    t=rgba[:,:,:3]
    mask=(rgba[:,:,3]>=190).astype(np.float64)
    nonzero=float(mask.sum())
    if nonzero<150:raise IsolationError("NATIVE_CURSOR_TEMPLATE_ALPHA_INVALID")
    err=np.zeros((target.shape[0]-mask.shape[0]+1,
                  target.shape[1]-mask.shape[1]+1),dtype=np.float64)
    for ch in range(3):
        A=target[:,:,ch];S=t[:,:,ch]
        err+=_valid_conv(A*A,mask)-2*_valid_conv(A,mask*S)+float(np.sum(mask*S*S))
    rmse=np.sqrt(np.maximum(err,0)/(3*nonzero))
    y,x=np.unravel_index(int(np.argmin(rmse)),rmse.shape)
    score=float(rmse[y,x])
    allowed=(ALLOWED_X[0]<=x<=ALLOWED_X[1] and
             ALLOWED_Y[0]<=y<=ALLOWED_Y[1] and score<=MAX_RMSE)
    return {"schema":"OpenZork.NativeGameCursorInputPreflight.v1",
        "status":"POSITIVE_SOURCE_CURSOR_ON_NEW_GAME" if allowed else "BLOCKED_CURSOR_NOT_ON_TARGET",
        "authorized_single_mouse_click":bool(allowed),
        "source_sprite_sha256":EXPECTED_SHA,
        "original_frame_sha256":sha(img),
        "WGC_native_size":[644,557],
        "best_cursor_top_left":[int(x),int(y)],
        "best_template_RGB_RMSE":round(score,4),
        "allowed_position_x":list(ALLOWED_X),"allowed_position_y":list(ALLOWED_Y),
        "max_RMSE":MAX_RMSE,
        "evidence_level":"PRE_CLICK_INPUT_ADMISSION_ONLY",
        "gameplay_success_claim":False,
        "fidelity_verified":False}
