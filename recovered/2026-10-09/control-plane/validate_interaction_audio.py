import json, re, sys
from pathlib import Path

ALLOWED={"SOURCE_AUDIO_VERIFIED","NO_AUDIO_BY_SOURCE","HOLD_UNRESOLVED"}

def validate(entries):
    failures=[]
    for i,e in enumerate(entries):
        key=e.get("interaction_id",f"index:{i}")
        c=e.get("classification")
        if c not in ALLOWED:
            failures.append({"interaction":key,"reason":"UNCLASSIFIED"})
            continue
        if not e.get("source_evidence"):
            failures.append({"interaction":key,"reason":"MISSING_SOURCE_EVIDENCE"})
        if c=="SOURCE_AUDIO_VERIFIED":
            asset=e.get("asset_if_any")
            sha=e.get("asset_sha256_if_any")
            if asset and (not isinstance(sha,str) or re.fullmatch(r"[0-9a-fA-F]{64}",sha) is None):
                failures.append({"interaction":key,"reason":"MISSING_ASSET_HASH"})
            if e.get("test_status")!="PASS":
                failures.append({"interaction":key,"reason":"VERIFIED_AUDIO_NOT_PASS"})
        elif c=="NO_AUDIO_BY_SOURCE":
            emitted=e.get("observed_audio_events",[])
            if emitted:
                failures.append({"interaction":key,"reason":"FORBIDDEN_AUDIO_EMITTED","events":emitted})
        elif c=="HOLD_UNRESOLVED":
            if e.get("guessed_audio") or e.get("asset_if_any"):
                failures.append({"interaction":key,"reason":"GUESSED_AUDIO_ON_HOLD"})
    return failures

def main():
    p=Path(sys.argv[1]); d=json.loads(p.read_text(encoding="utf-8-sig"))
    entries=d if isinstance(d,list) else d.get("entries",d.get("interactions",[]))
    failures=validate(entries)
    out={"schema":"InteractionAudioFidelityVerification.v1","input":str(p),"checked":len(entries),"failures":failures,"status":"PASS" if not failures else "FAIL"}
    print(json.dumps(out,indent=2))
    return 0 if not failures else 1
if __name__=="__main__": raise SystemExit(main())
