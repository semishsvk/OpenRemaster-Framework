"""Synthetic-only process loopback audio canary. No game audio and no desktop mix."""
from datetime import datetime,timezone
import io,json,math,os,subprocess,sys,time,uuid,wave,struct
from pathlib import Path
from fidelity_path import workspace_root, load_process_identity, sha256, outfile

ROOT=workspace_root()
EXE=Path(__file__).with_name("capture_process_audio.exe")

def audio_child(marker,play):
    import winsound
    p=load_process_identity(os.getpid())
    Path(marker).write_text(json.dumps({"pid":os.getpid(),"creation_ticks_100ns":p["creation_ticks_100ns"],"audible":play}))
    if play:
        time.sleep(1.1)
        wav=io.BytesIO()
        with wave.open(wav,"wb") as w:
            w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100)
            payload=bytearray()
            for i in range(int(44100*1.4)):
                v=int(1000*math.sin(2*math.pi*440*i/44100))
                payload.extend(struct.pack("<hh",v,v))
            w.writeframes(bytes(payload))
        winsound.PlaySound(wav.getvalue(),winsound.SND_MEMORY)
        time.sleep(1.1)
    else:
        time.sleep(8)

def start_child(base,play):
    marker=base/("audible.json" if play else "silent.json")
    proc=subprocess.Popen([sys.executable,"-B",str(Path(__file__)),"--child",str(marker),"1" if play else "0"],
         stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    until=time.monotonic()+7
    while not marker.exists() and time.monotonic()<until and proc.poll() is None:
        time.sleep(.03)
    if not marker.exists():
        out,err=proc.communicate()
        raise AssertionError(str((out[-1000:],err[-1200:])))
    return proc,json.loads(marker.read_text())

def terminate(proc):
    if proc.poll() is None:
        proc.terminate()
    try:proc.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill();proc.communicate(timeout=3)

def call(identity,duration,dest):
    argv=[str(EXE),str(identity["pid"]),str(identity["creation_ticks_100ns"]),str(duration),str(dest)]
    p=subprocess.run(argv,text=True,capture_output=True,timeout=duration/1000+14)
    return {"exit":p.returncode,"stdout":p.stdout.strip(),"stderr":p.stderr.strip()}

def rms(path):
    with wave.open(str(path),"rb") as w:
        assert w.getframerate()==44100 and w.getnchannels()==2 and w.getsampwidth()==2
        raw=w.readframes(w.getnframes())
        assert len(raw)%2==0
        import numpy as np
        data=np.frombuffer(raw,dtype="<i2").astype("float64")
        return (float(np.sqrt(np.mean(data*data))) if data.size else 0.0,
                len(raw),w.getnframes(), int(np.max(np.abs(data))) if data.size else 0)

def main():
    assert EXE.exists()
    base=ROOT/"runtime-test"/"results"/("process-loopback-"+uuid.uuid4().hex[:8])
    base.mkdir()
    aud,aid=start_child(base,True)
    try:
        wav=base/"process-0001.wav"
        r=call(aid,3600,wav)
        if r["exit"]!=0 or not wav.is_file():
            raise AssertionError("Audible process capture failed: "+str(r))
        met=json.loads(r["stdout"])
        value,nb,frames,peak=rms(wav)
        assert frames>=5000 and value>5,(frames,value,met)
    finally: terminate(aud)

    silent,sid=start_child(base,False)
    outsider,oid=start_child(base,True)
    try:
        silence_path=base/"silent-target.wav"
        r2=call(sid,3500,silence_path)
        if r2["exit"]!=0 or not silence_path.is_file():
            raise AssertionError("Silent target capture failed: "+str(r2))
        blank,nb2,fr2,silent_peak=rms(silence_path)
        # PCM conversion may add +/-1 LSB noise. Reject foreign content, not quantization dither.
        assert blank<1.0 and silent_peak<=1 and value>blank*100,(blank,silent_peak,value,r2)
        wrong=base/"wrong.wav"
        neg=call({"pid":os.getpid(),"creation_ticks_100ns":sid["creation_ticks_100ns"]},500,wrong)
        assert neg["exit"]!=0 and not wrong.exists(),neg
    finally:
        terminate(silent);terminate(outsider)
    report={"schema":"OpenRemaster.ProcessLoopbackSyntheticCanary.v1",
            "status":"PASS","date_utc":datetime.now(timezone.utc).isoformat(),
            "binary_sha256":sha256(EXE),"audible_pid":aid["pid"],"audible_rms":round(value,4),
            "audible_frames":frames,"audible_sha256":sha256(wav),
            "silent_pid":sid["pid"],"unrelated_audible_pid":oid["pid"],
            "silent_with_foreign_playback_rms":blank,"silent_frames":fr2,
            "silent_max_abs_sample":silent_peak,"audible_peak":peak,
            "wrong_creation_ticks_rejected":True,
            "actual_original_game_audio_fidelity":"NOT_TESTED","result_directory":str(base)}
    (base/"audio-canary.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report))

if __name__=="__main__":
    if "--child" in sys.argv:
        audio_child(sys.argv[2],sys.argv[3]=="1")
    else:
        main()
