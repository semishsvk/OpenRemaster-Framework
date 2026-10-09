"""Single-owned-HWND client-coordinate diagnostic mouse post.
No global OS cursor, focus switching, desktop pixel injection, or SDL fidelity claim.
Rejection conditions are deliberately conservative.
"""
import ctypes
from ctypes import wintypes as W
import os,time
from datetime import datetime,timezone
from fidelity_runtime_isolation_v1 import IsolationError,assert_window_owned

U=ctypes.WinDLL("user32",use_last_error=True) if os.name=="nt" else None
class POINT(ctypes.Structure):
    _fields_=(("x",W.LONG),("y",W.LONG))
class RECT(ctypes.Structure):
    _fields_=(("left",W.LONG),("top",W.LONG),("right",W.LONG),("bottom",W.LONG))

def owned_client_dimensions(hwnd,pid,creation_ticks,exe):
    if os.name!="nt":raise IsolationError("OWNED_MOUSE_WIN32_ONLY")
    assert_window_owned(hwnd,pid,creation_ticks,exe)
    U.GetClientRect.argtypes=(W.HWND,ctypes.POINTER(RECT))
    U.GetClientRect.restype=W.BOOL
    U.IsIconic.argtypes=(W.HWND,)
    U.IsIconic.restype=W.BOOL
    if U.IsIconic(int(hwnd)):
        raise IsolationError("OWNED_MOUSE_WINDOW_MINIMIZED")
    rect=RECT()
    if not U.GetClientRect(int(hwnd),ctypes.byref(rect)):
        raise IsolationError("OWNED_MOUSE_GET_CLIENT_RECT_FAILED")
    w,h=rect.right-rect.left,rect.bottom-rect.top
    if not (100<=w<=8192 and 100<=h<=8192):
        raise IsolationError("OWNED_MOUSE_CLIENT_SIZE_INVALID")
    return w,h

def post_owned_left_click(hwnd,pid,creation_ticks,exe,x,y,hold_ms=110):
    if type(x) is not int or type(y) is not int:
        raise IsolationError("OWNED_MOUSE_COORDINATE_NONINTEGER")
    w,h=owned_client_dimensions(hwnd,pid,creation_ticks,exe)
    if not (8<=x<w-8 and 8<=y<h-8):
        raise IsolationError("OWNED_MOUSE_CLICK_OUTSIDE_CLIENT",{"width":w,"height":h,"x":x,"y":y})
    if not (50<=hold_ms<=250):
        raise IsolationError("OWNED_MOUSE_HOLD_TIME_INVALID")
    U.PostMessageW.argtypes=(W.HWND,W.UINT,W.WPARAM,W.LPARAM)
    U.PostMessageW.restype=W.BOOL
    lp=(x&0xffff)|((y&0xffff)<<16)
    assert_window_owned(hwnd,pid,creation_ticks,exe)
    if not U.PostMessageW(int(hwnd),0x0200,0,lp):
        raise IsolationError("OWNED_MOUSE_MOVE_NOT_POSTED")
    time.sleep(0.06)
    assert_window_owned(hwnd,pid,creation_ticks,exe)
    if not U.PostMessageW(int(hwnd),0x0201,0x0001,lp):
        raise IsolationError("OWNED_MOUSE_DOWN_NOT_POSTED")
    time.sleep(hold_ms/1000)
    assert_window_owned(hwnd,pid,creation_ticks,exe)
    if not U.PostMessageW(int(hwnd),0x0202,0,lp):
        raise IsolationError("OWNED_MOUSE_UP_NOT_POSTED")
    return {"schema":"OpenRemaster.HwndOwnedMouseDiagnosticEvent.v1",
       "hwnd":int(hwnd),"pid":int(pid),"creation_ticks_100ns":creation_ticks,
       "client_x":x,"client_y":y,"client_width":w,"client_height":h,
       "action":"MOUSE_LEFT_CLICK",
       "delivery":"POSTED_NOT_SDL_OR_GAME_CONSUMPTION_PROOF",
       "global_SendInput_used":False,
       "global_SetCursorPos_used":False,
       "focus_switched":False,
       "timestamp_utc":datetime.now(timezone.utc).isoformat()}
