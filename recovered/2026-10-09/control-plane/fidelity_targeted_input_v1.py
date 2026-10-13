"""Windows HWND-owned diagnostic keyboard. NO SendInput, focus changes or global keys.
Posting an event is NOT proof that game state consumed it. Image/state replay required.
"""
import ctypes
from ctypes import wintypes
import os,time
from datetime import datetime,timezone
from fidelity_runtime_isolation_v1 import IsolationError,assert_window_owned

ALLOWED_VK={"SPACE":0x20,"ENTER":0x0D,"ESCAPE":0x1B,
            "LEFT":0x25,"UP":0x26,"RIGHT":0x27,"DOWN":0x28}
U=ctypes.WinDLL("user32",use_last_error=True) if os.name=="nt" else None

def has_owned_mouse_action(plan):
    return isinstance(plan,list) and any(isinstance(event,dict) and "action" in event for event in plan)

def validate_plan(plan,delay):
    if not isinstance(plan,list) or not 1<=len(plan)<=8:
        raise IsolationError("OWNED_INPUT_PLAN_SIZE_INVALID")
    last=-1.0
    for i,event in enumerate(plan):
        if not isinstance(event,dict):
            raise IsolationError("OWNED_INPUT_PLAN_EVENT_INVALID",{"index":i})
        try:at=float(event["at_seconds"])
        except (TypeError,ValueError,KeyError):
            raise IsolationError("OWNED_INPUT_PLAN_TIME_INVALID",{"index":i})
        if "key" in event:
            if set(event)!={"at_seconds","key"}:
                raise IsolationError("OWNED_INPUT_PLAN_EVENT_INVALID",{"index":i})
            if event["key"] not in ALLOWED_VK:
                raise IsolationError("OWNED_INPUT_PLAN_UNSAFE_EVENT",{"index":i,"key":event["key"]})
        else:
            if set(event)!={"at_seconds","action","client_x","client_y"}:
                raise IsolationError("OWNED_INPUT_PLAN_EVENT_INVALID",{"index":i})
            if event["action"]!="MOUSE_LEFT_CLICK":
                raise IsolationError("OWNED_INPUT_PLAN_UNSAFE_EVENT",{"index":i,"action":event["action"]})
            if type(event["client_x"]) is not int or type(event["client_y"]) is not int:
                raise IsolationError("OWNED_INPUT_PLAN_MOUSE_COORDINATE_INVALID",{"index":i})
            if not 8<=event["client_x"]<=8191 or not 8<=event["client_y"]<=8191:
                raise IsolationError("OWNED_INPUT_PLAN_MOUSE_COORDINATE_INVALID",{"index":i})
        if at<0.1 or at<=last or at>float(delay)-0.5:
            raise IsolationError("OWNED_INPUT_PLAN_UNSAFE_EVENT",{"index":i,"at_seconds":at})
        last=at
    return True

def send_owned_key(hwnd,pid,creation_ticks,exe,key,hold_ms=130):
    if os.name!="nt" or key not in ALLOWED_VK:
        raise IsolationError("OWNED_INPUT_KEY_NOT_SUPPORTED")
    U.PostMessageW.argtypes=(wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM)
    U.PostMessageW.restype=wintypes.BOOL
    U.MapVirtualKeyW.argtypes=(wintypes.UINT,wintypes.UINT)
    U.MapVirtualKeyW.restype=wintypes.UINT
    assert_window_owned(hwnd,pid,creation_ticks,exe)
    vk=ALLOWED_VK[key]
    scan=int(U.MapVirtualKeyW(vk,0))
    base=1 | (scan<<16)
    if not U.PostMessageW(hwnd,0x0100,vk,base):
        raise IsolationError("OWNED_KEYDOWN_NOT_POSTED")
    time.sleep(max(0.04,min(0.25,hold_ms/1000)))
    assert_window_owned(hwnd,pid,creation_ticks,exe)
    if not U.PostMessageW(hwnd,0x0101,vk,base|(1<<30)|(1<<31)):
        raise IsolationError("OWNED_KEYUP_NOT_POSTED")
    return {"schema":"OpenRemaster.HwndOwnedInputEvent.v1",
            "pid":pid,"hwnd":hwnd,"creation_ticks_100ns":creation_ticks,
            "key":key,"delivery":"POSTED_NOT_GAME_CONSUMPTION_PROOF",
            "timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "global_SendInput_used":False,"focus_switched":False}

def execute_targeted_plan(identity,window,plan,delay,poll_exit):
    validate_plan(plan,delay)
    start=time.monotonic()
    records=[]
    for event in plan:
        when=start+float(event["at_seconds"])
        while time.monotonic()<when:
            if poll_exit() is not None:
                raise IsolationError("OWNED_RUNTIME_EXITED_BEFORE_INPUT")
            assert_window_owned(window["hwnd"],identity["pid"],
                                identity["creation_ticks_100ns"],identity["executable"])
            time.sleep(min(.10,max(0,when-time.monotonic())))
        if "key" in event:
            proof=send_owned_key(window["hwnd"],identity["pid"],
                                 identity["creation_ticks_100ns"],identity["executable"],event["key"])
        else:
            from fidelity_owned_mouse_v1 import post_owned_left_click
            proof=post_owned_left_click(window["hwnd"],identity["pid"],
                identity["creation_ticks_100ns"],identity["executable"],
                event["client_x"],event["client_y"])
        proof["scheduled_at_seconds"]=event["at_seconds"]
        proof["observed_offset_seconds"]=round(time.monotonic()-start,3)
        records.append(proof)
    return records,start
