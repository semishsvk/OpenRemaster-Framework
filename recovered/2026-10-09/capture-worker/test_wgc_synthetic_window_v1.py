"""Non-game Win32 canary: verify native HWND-bound Windows.Graphics.Capture.
Never manipulates game windows, never captures RDC desktop, never asserts game fidelity.
"""
import ctypes
from ctypes import wintypes as W
from datetime import datetime, timezone
import json, os, subprocess, sys, time, uuid
from pathlib import Path
from PIL import Image, ImageStat
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "control-plane"))
from fidelity_runtime_isolation_v1 import process_identity, sha256
from fidelity_local_capture_wgc_v1 import acquire_bound_wgc_frame
from fidelity_local_audio_loopback_v1 import capture_process_audio
from fidelity_runtime_worker_v1 import validate_capture

ROOT=Path(__file__).resolve().parents[2]
WGC=Path(__file__).with_name("capture_window_wgc.exe")
U=ctypes.WinDLL("user32",use_last_error=True)
G=ctypes.WinDLL("gdi32",use_last_error=True)
K=ctypes.WinDLL("kernel32",use_last_error=True)

LRESULT=ctypes.c_ssize_t
PROC=ctypes.WINFUNCTYPE(LRESULT, W.HWND, W.UINT, ctypes.c_size_t, ctypes.c_ssize_t)
class RC(ctypes.Structure):
    _fields_=[("left",W.LONG),("top",W.LONG),("right",W.LONG),("bottom",W.LONG)]
class PAINTSTRUCT(ctypes.Structure):
    _fields_=[("hdc",W.HDC),("fErase",W.BOOL),("rcPaint",RC),
              ("fRestore",W.BOOL),("fIncUpdate",W.BOOL),("rgbReserved",ctypes.c_byte*32)]
class WNDCLASSEXW(ctypes.Structure):
    _fields_=[("cbSize",W.UINT),("style",W.UINT),("lpfnWndProc",PROC),
              ("cbClsExtra",ctypes.c_int),("cbWndExtra",ctypes.c_int),
              ("hInstance",W.HINSTANCE),("hIcon",W.HICON),("hCursor",W.HCURSOR),
              ("hbrBackground",W.HBRUSH),("lpszMenuName",W.LPCWSTR),
              ("lpszClassName",W.LPCWSTR),("hIconSm",W.HICON)]
class POINT(ctypes.Structure):
    _fields_=[("x",W.LONG),("y",W.LONG)]
class MSG(ctypes.Structure):
    _fields_=[("hwnd",W.HWND),("message",W.UINT),("wParam",ctypes.c_size_t),
              ("lParam",ctypes.c_ssize_t),("time",W.DWORD),("pt",POINT)]

U.DefWindowProcW.argtypes=(W.HWND,W.UINT,ctypes.c_size_t,ctypes.c_ssize_t)
U.DefWindowProcW.restype=LRESULT
U.RegisterClassExW.argtypes=(ctypes.POINTER(WNDCLASSEXW),)
U.RegisterClassExW.restype=W.ATOM
U.CreateWindowExW.argtypes=(W.DWORD,W.LPCWSTR,W.LPCWSTR,W.DWORD,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,W.HWND,W.HMENU,W.HINSTANCE,ctypes.c_void_p)
U.CreateWindowExW.restype=W.HWND
U.BeginPaint.argtypes=(W.HWND,ctypes.POINTER(PAINTSTRUCT))
U.BeginPaint.restype=W.HDC
U.EndPaint.argtypes=(W.HWND,ctypes.POINTER(PAINTSTRUCT))
U.GetClientRect.argtypes=(W.HWND,ctypes.POINTER(RC))
U.FillRect.argtypes=(W.HDC,ctypes.POINTER(RC),W.HBRUSH)
G.CreateSolidBrush.argtypes=(W.DWORD,)
G.CreateSolidBrush.restype=W.HBRUSH
G.DeleteObject.argtypes=(W.HGDIOBJ,)
U.ShowWindow.argtypes=(W.HWND,ctypes.c_int)
U.UpdateWindow.argtypes=(W.HWND,)
U.PeekMessageW.argtypes=(ctypes.POINTER(MSG),W.HWND,W.UINT,W.UINT,W.UINT)
U.TranslateMessage.argtypes=(ctypes.POINTER(MSG),)
U.DispatchMessageW.argtypes=(ctypes.POINTER(MSG),)
K.GetModuleHandleW.argtypes=(W.LPCWSTR,)
K.GetModuleHandleW.restype=W.HMODULE

def child(marker_path):
    colors=(0x000000FA,0x00FC0000)
    import threading,io,math,wave,struct,winsound
    play_signal=Path(marker_path).parent/"play-signal"
    def play_tone():
        until=time.monotonic()+18
        while not play_signal.exists() and time.monotonic()<until:
            time.sleep(0.03)
        if not play_signal.exists():
            return
        time.sleep(0.6)
        bio=io.BytesIO()
        with wave.open(bio,"wb") as w:
            w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100)
            raw=bytearray()
            for i in range(int(44100*1.3)):
                x=int(1000*math.sin(2*math.pi*440*i/44100))
                raw.extend(struct.pack("<hh",x,x))
            w.writeframes(bytes(raw))
        winsound.PlaySound(bio.getvalue(),winsound.SND_MEMORY)
    threading.Thread(target=play_tone,daemon=True).start()
    @PROC
    def wndproc(hwnd,msg,wparam,lparam):
        if msg==0x000F:
            ps=PAINTSTRUCT()
            hdc=U.BeginPaint(hwnd,ctypes.byref(ps))
            box=RC()
            U.GetClientRect(hwnd,ctypes.byref(box))
            half=(box.right-box.left)//2
            a=RC(0,0,half,box.bottom)
            b=RC(half,0,box.right,box.bottom)
            left=G.CreateSolidBrush(colors[0])
            right=G.CreateSolidBrush(colors[1])
            U.FillRect(hdc,ctypes.byref(a),left)
            U.FillRect(hdc,ctypes.byref(b),right)
            G.DeleteObject(left);G.DeleteObject(right)
            U.EndPaint(hwnd,ctypes.byref(ps))
            return 0
        if msg==0x0002:
            U.PostQuitMessage(0)
            return 0
        return U.DefWindowProcW(hwnd,msg,wparam,lparam)
    klass="ORF_WGC_Synthetic_"+uuid.uuid4().hex[:8]
    instance=K.GetModuleHandleW(None)
    wc=WNDCLASSEXW()
    wc.cbSize=ctypes.sizeof(wc)
    wc.lpfnWndProc=wndproc
    wc.hInstance=instance
    wc.lpszClassName=klass
    atom=U.RegisterClassExW(ctypes.byref(wc))
    if not atom:
        raise OSError(ctypes.get_last_error(),"RegisterClassEx failed")
    hwnd=U.CreateWindowExW(0x08000080,klass,"ORF isolated color probe",
                           0x00CF0000,120,120,420,300,None,None,instance,None)
    if not hwnd:
        raise OSError(ctypes.get_last_error(),"CreateWindowEx failed")
    U.ShowWindow(hwnd,4)
    U.UpdateWindow(hwnd)
    ident=process_identity(os.getpid())
    Path(marker_path).write_text(json.dumps({"hwnd":int(hwnd),"pid":os.getpid(),
        "creation_ticks_100ns":ident["creation_ticks_100ns"]}))
    until=time.monotonic()+25
    message=MSG()
    while time.monotonic()<until:
        while U.PeekMessageW(ctypes.byref(message),None,0,0,1):
            if message.message==0x12: return
            U.TranslateMessage(ctypes.byref(message))
            U.DispatchMessageW(ctypes.byref(message))
        time.sleep(0.015)
    U.DestroyWindow(hwnd)

def run_canary():
    assert WGC.is_file()
    base=ROOT/"runtime-test"/"results"/("wgc-synthetic-"+uuid.uuid4().hex[:10])
    base.mkdir(parents=True)
    marker=base/"window-identity.json"
    process=subprocess.Popen([sys.executable,"-B",str(Path(__file__)),"--child",str(marker)],
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    try:
        until=time.monotonic()+8
        while not marker.is_file() and process.poll() is None and time.monotonic()<until:
            time.sleep(0.05)
        if not marker.is_file():
            out,err=process.communicate(timeout=2)
            raise AssertionError("Synthetic window did not start: "+str((process.returncode,out[-500:],err[-1000:])))
        data=json.loads(marker.read_text())
        frame=base/"frame-0001.bmp"
        argv=[str(WGC),str(data["hwnd"]),str(data["pid"]),str(data["creation_ticks_100ns"]),str(frame)]
        capture=subprocess.run(argv,text=True,capture_output=True,timeout=12)
        if capture.returncode:
            raise AssertionError("WGC capture failed: "+json.dumps({"code":capture.returncode,"stdout":capture.stdout[-500:],"stderr":capture.stderr[-700:]}))
        assert frame.is_file() and frame.stat().st_size>4096
        with Image.open(frame) as im:
            im.load()
            assert im.width>=200 and im.height>=100,(im.width,im.height)
            first=im.convert("RGB").getpixel((im.width//4,im.height//2))
            second=im.convert("RGB").getpixel((im.width*3//4,im.height//2))
            diff=sum(abs(a-b) for a,b in zip(first,second))
            if diff<200:
                raise AssertionError(f"Window target not recovered as red+blue pattern: {first} vs {second}")
            dims=[im.width,im.height]
        ident=process_identity(data["pid"])
        assert ident and ident["creation_ticks_100ns"]==data["creation_ticks_100ns"]
        ident["executable_sha256"]=sha256(ident["executable"])
        window={"hwnd":data["hwnd"],"pid":data["pid"],"title":"ORF isolated color probe"}
        proof_dir=base/"attached"
        acquired=acquire_bound_wgc_frame(proof_dir,ident,window,"wgc-synthetic-attestation-v1")
        proof=validate_capture(proof_dir,ident,window,"wgc-synthetic-attestation-v1",False)
        assert proof["manifest_sha256"]==acquired["manifest_sha256"]
        assert proof["frames"][0]["sha256"]==acquired["frame_sha256"]
        (base/"play-signal").write_text("start")
        audio= capture_process_audio(proof_dir,ident,duration_ms=3000)
        audio_proof=validate_capture(proof_dir,ident,window,"wgc-synthetic-attestation-v1",True)
        assert len(audio_proof["audio"])==1
        assert audio["nonzero_samples"]>3000, audio
        wrong=base/"wrong-owner.bmp"
        neg=subprocess.run([str(WGC),str(data["hwnd"]),str(os.getpid()),str(data["creation_ticks_100ns"]),str(wrong)],
                           text=True,capture_output=True,timeout=5)
        assert neg.returncode!=0 and not wrong.exists(),(neg.returncode,neg.stdout,neg.stderr)
        report={"schema":"OpenRemaster.WGCNativeSyntheticCanary.v1","status":"PASS",
            "timestamp":datetime.now(timezone.utc).isoformat(),
            "backend":"windows_graphics_capture","native_binary_sha256":sha256(WGC),
            "window":data,"bmp_dimensions":dims,"color_one":first,"color_two":second,
            "pixel_difference":diff,"frame_sha256":sha256(frame),
            "capture_attestation_sha256":audio_proof["manifest_sha256"],
            "bound_producer_result":acquired,
            "process_audio_sha256":audio["wav_sha256"],
            "process_audio_frames":audio["frames"],
            "process_audio_nonzero_samples":audio["nonzero_samples"],
            "wrong_pid_rejected":True,
            "rdc_stream_used":False,"original_game_fidelity":"NOT_TESTED",
            "frame_path":str(frame)}
        (base/"canary-result.json").write_text(json.dumps(report,indent=2))
        print(json.dumps(report))
    finally:
        if process.poll() is None: process.terminate()
        try:process.communicate(timeout=4)
        except subprocess.TimeoutExpired:
            process.kill();process.communicate(timeout=4)

if __name__=="__main__":
    if len(sys.argv)>1 and sys.argv[1]=="--child": child(sys.argv[2])
    else: run_canary()
