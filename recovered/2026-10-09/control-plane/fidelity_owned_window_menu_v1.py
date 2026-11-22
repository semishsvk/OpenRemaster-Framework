"""Win32 menu inventory bound to an exactly identified HWND. No input or focus changes."""
import ctypes,os
from ctypes import wintypes
from fidelity_runtime_isolation_v1 import IsolationError,assert_window_owned
U=ctypes.WinDLL("user32",use_last_error=True) if os.name=="nt" else None
if U:
 U.GetMenu.argtypes=(wintypes.HWND,)
 U.GetMenu.restype=wintypes.HMENU
 U.GetMenuItemCount.argtypes=(wintypes.HMENU,)
 U.GetMenuItemCount.restype=ctypes.c_int
 U.GetSubMenu.argtypes=(wintypes.HMENU,ctypes.c_int)
 U.GetSubMenu.restype=wintypes.HMENU
 U.GetMenuStringW.argtypes=(wintypes.HMENU,wintypes.UINT,wintypes.LPWSTR,ctypes.c_int,wintypes.UINT)
 U.GetMenuStringW.restype=ctypes.c_int
 U.GetMenuItemID.argtypes=(wintypes.HMENU,ctypes.c_int)
 U.GetMenuItemID.restype=wintypes.UINT

def post_bound_dosboxx_quit(hwnd,pid,creation_ticks,exe):
    """Send only the discovered, exact DOSBox-X Main > Quit menu command.
    Must never send menu command to any unowned window; menu IDs can differ by version.
    """
    from pathlib import Path
    if Path(exe).name.lower()!="dosbox-x.exe":
        raise IsolationError("OWNED_MENU_QUIT_REQUIRES_DOSBOX_X")
    menu=inspect_bound_window_menu(hwnd,pid,creation_ticks,exe,max_depth=1)
    candidates=[]
    for heading in menu.get("items",[]):
        if heading.get("label")!="Main":
            continue
        for item in heading.get("children",[]):
            if item.get("label","").startswith("Quit from DOSBox-X") and item.get("id"):
                candidates.append(item)
    if len(candidates)!=1:
        raise IsolationError("OWNED_MENU_QUIT_ITEM_NOT_UNIQUE",{"count":len(candidates)})
    command_id=int(candidates[0]["id"])
    if not (1<=command_id<=0xffff):
        raise IsolationError("OWNED_MENU_COMMAND_ID_INVALID")
    U.PostMessageW.argtypes=(wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM)
    U.PostMessageW.restype=wintypes.BOOL
    assert_window_owned(hwnd,pid,creation_ticks,exe)
    if not U.PostMessageW(hwnd,0x0111,command_id,0):
        raise IsolationError("OWNED_DOSBOXX_MENU_QUIT_NOT_POSTED")
    return {"schema":"OpenRemaster.OwnedDOSBoxXMenuQuit.v1",
            "hwnd":int(hwnd),"pid":int(pid),"creation_ticks_100ns":creation_ticks,
            "menu_label":"Quit from DOSBox-X","menu_id":command_id,
            "delivery":"POSTED_UNVERIFIED_UNTIL_PROCESS_EXIT","global_input_used":False}

def inspect_bound_window_menu(hwnd,pid,creation_ticks,exe,max_depth=3):
 assert_window_owned(hwnd,pid,creation_ticks,exe)
 menu=U.GetMenu(int(hwnd))
 if not menu:return {"status":"NO_WINDOW_MENU","items":[]}
 def walk(menu,depth=0):
  if depth>max_depth:return []
  count=U.GetMenuItemCount(menu)
  if not 0<=count<=250:raise IsolationError("OWNER_MENU_ITEM_COUNT_INVALID")
  out=[]
  for i in range(count):
   label=ctypes.create_unicode_buffer(250)
   U.GetMenuStringW(menu,i,label,len(label),0x400)
   submenu=U.GetSubMenu(menu,i)
   item_id=U.GetMenuItemID(menu,i)
   record={"label":label.value,"id":int(item_id) if item_id !=0xffffffff else None,
           "index":i}
   if submenu:record["children"]=walk(submenu,depth+1)
   out.append(record)
  return out
 items=walk(menu)
 assert_window_owned(hwnd,pid,creation_ticks,exe)
 return {"schema":"FidelityBoundWindowMenuInventory.v1","status":"READ_ONLY",
         "pid":pid,"hwnd":int(hwnd),"items":items}
