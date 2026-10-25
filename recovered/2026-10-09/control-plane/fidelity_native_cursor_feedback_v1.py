"""Experimental bounded image-feedback calibration of ORIGINAL ZORKDOS cursor.
Uses only local WGC frame pixels, original extracted sprite, and guest-relative
input ports. No host OS pointer, focus or screenshot from remote desktop stream.
Any uncertainty fails closed. This is NOT original-vs-Godot fidelity authority.
"""
from pathlib import Path
import numpy as np
from PIL import Image
from fidelity_original_cursor_gate_v1 import (
 evaluate_original_newgame_cursor,TEMPLATE,EXPECTED_SHA,sha)
from fidelity_runtime_isolation_v1 import IsolationError

TARGET=(317,421)
MAX_MOTION_PER_AXIS=200
MAX_RECALIBRATIONS=4

def detect_extracted_cursor_position(file):
    """Locate full sprite (conservative global match), else partially clipped left sprite."""
    baseline=evaluate_original_newgame_cursor(file)
    bx,by=baseline["best_cursor_top_left"]
    if baseline["best_template_RGB_RMSE"]<=70:
        return {"schema":"OpenZork.NativeCursorPositionEvidence.v1",
          "status":"ORIGINAL_SPRITE_MATCHED_FULL","x":bx,"y":by,
          "score":baseline["best_template_RGB_RMSE"],
          "source_frame_sha256":baseline["original_frame_sha256"],
          "source_sprite_sha256":EXPECTED_SHA,
          "NewGame_click_allowed":baseline["authorized_single_mouse_click"]}
    with Image.open(file) as im:
        im=im.convert("RGB")
        if im.size!=(644,557):
            raise IsolationError("CURSOR_FEEDBACK_GEOMETRY_UNSUPPORTED")
        frame=np.asarray(im,dtype=np.int16)
    with Image.open(TEMPLATE) as im:
        src=np.asarray(im.convert("RGBA"),dtype=np.int16)
    rgb=src[:,:,:3];opaque=src[:,:,3]>=190
    H,W=frame.shape[:2];th,tw=opaque.shape
    results=[]
    for x in range(-28,20):
        x0=max(0,-x);x1=min(tw,W-x)
        if x1<=x0:continue
        for y in range(0,H-th+1):
            mask=opaque[:,x0:x1]
            area=int(mask.sum())
            if area<300:continue
            actual=frame[y:y+th,x+x0:x+x1][mask]
            ideal=rgb[:,x0:x1][mask]
            rmse=float(np.sqrt(np.mean((actual.astype(np.float32)-ideal.astype(np.float32))**2)))
            results.append((rmse,x,y,area))
    if results:
        best=min(results)
        if best[0]<15:
            return {"schema":"OpenZork.NativeCursorPositionEvidence.v1",
             "status":"ORIGINAL_SPRITE_MATCHED_LEFT_CLIPPED",
             "x":best[1],"y":best[2],"score":round(best[0],4),
             "visible_alpha_pixels":best[3],
             "source_frame_sha256":baseline["original_frame_sha256"],
             "source_sprite_sha256":EXPECTED_SHA,
             "NewGame_click_allowed":False}
    return {"schema":"OpenZork.NativeCursorPositionEvidence.v1",
      "status":"CURSOR_POSITION_UNKNOWN_FAIL_CLOSED",
      "x":None,"y":None,"score":None,
      "source_frame_sha256":baseline["original_frame_sha256"],
      "source_sprite_sha256":EXPECTED_SHA,
      "NewGame_click_allowed":False}

def safe_positive_feedback_delta(observed):
    if observed.get("NewGame_click_allowed"):
        return {"status":"ALREADY_ON_NEW_GAME","x_delta":0,"y_delta":0}
    x,y=observed.get("x"),observed.get("y")
    if type(x) is not int or type(y) is not int:
        raise IsolationError("CURSOR_FEEDBACK_POSITION_UNKNOWN")
    dx=TARGET[0]-x;dy=TARGET[1]-y
    if dx<0 or dy<0:
        raise IsolationError("CURSOR_FEEDBACK_NEGATIVE_MOVEMENT_UNSUPPORTED",
                            {"position":[x,y],"target":list(TARGET)})
    if dx==0 and dy==0:
        raise IsolationError("CURSOR_FEEDBACK_AT_TARGET_BUT_TEMPLATE_NOT_AUTHORIZED")
    return {"status":"GUEST_POSITIVE_MOVE_ONLY",
       "x_delta":min(MAX_MOTION_PER_AXIS,dx),
       "y_delta":min(MAX_MOTION_PER_AXIS,dy),
       "source_cursor":[x,y],"target_cursor":list(TARGET)}

def guest_port_motion_value(axis,delta):
    if axis not in ("x","y") or type(delta) is not int or not 0<=delta<=MAX_MOTION_PER_AXIS:
        raise IsolationError("CURSOR_FEEDBACK_MOTION_OUTSIDE_BOUND")
    sub=0x09 if axis=="x" else 0x0a
    value=((delta+1)*256<<16)|(sub<<8)
    assert 0<=value<=0xffffffff
    return f"{value:08X}"
