"""Evidence-backed source/candidate scene pairing prerequisite for ZVision panorama tests.
This does NOT compare images or validate gameplay; it prevents accidental TA30-vs-VB30
visual acceptance. Game-specific panorama view coordinate contract = 0..1439.
"""
from pathlib import Path
import re,hashlib,json

ROOT=Path(__file__).resolve().parents[2]
WORK=(ROOT/"work").resolve()
EVIDENCE=(ROOT/"runtime-test"/"results").resolve()
OUTPUT=(ROOT/"output").resolve()

class ScenePairError(Exception):
    def __init__(self,reason,details=None):
        self.reason=reason
        self.details=details or {}
        super().__init__(reason)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _inside(path,roots):
    return any(root==path or root in path.parents for root in roots)

def validate_evidence_item(item,label):
    if not isinstance(item,dict):
        raise ScenePairError("PAIR_EVIDENCE_NOT_OBJECT",{"side":label})
    required=("game","scene","view","orientation_period",
             "capture_path","capture_sha256",
             "identity_provenance_path","identity_provenance_sha256")
    if not all(k in item for k in required):
        raise ScenePairError("PAIR_IDENTITY_OR_PROVENANCE_MISSING",{"side":label})
    if item["game"]!="OpenZork":
        raise ScenePairError("PAIR_GAME_PROFILE_NOT_COMMISSIONED",{"side":label})
    if not re.fullmatch(r"[A-Z]{2}[0-9]{2}",str(item["scene"])):
        raise ScenePairError("PAIR_SCENE_KEY_INVALID",{"side":label})
    if type(item["view"]) is not int or type(item["orientation_period"]) is not int:
        raise ScenePairError("PAIR_VIEW_NOT_INTEGER",{"side":label})
    if item["orientation_period"]!=1440 or not 0<=item["view"]<1440:
        raise ScenePairError("PAIR_PANORAMA_VIEW_OUT_OF_RANGE",{"side":label})
    for pair in (("capture_path","capture_sha256"),("identity_provenance_path","identity_provenance_sha256")):
        path=Path(item[pair[0]]).resolve()
        if not _inside(path,(EVIDENCE,OUTPUT,WORK)) or not path.is_file():
            raise ScenePairError("PAIR_EVIDENCE_PATH_UNAUTHORIZED_OR_MISSING",{"side":label,"path":str(path)})
        actual=sha(path)
        if actual!=item[pair[1]]:
            raise ScenePairError("PAIR_EVIDENCE_HASH_MISMATCH",{"side":label,"path":str(path)})
    return True

def attest_paired_scene(original,candidate):
    validate_evidence_item(original,"original")
    validate_evidence_item(candidate,"candidate")
    if original["game"]!=candidate["game"]:
        raise ScenePairError("PAIR_GAME_MISMATCH")
    if original["scene"]!=candidate["scene"]:
        raise ScenePairError("PAIR_SCENE_MISMATCH",
                             {"original":original["scene"],"candidate":candidate["scene"]})
    if original["view"]!=candidate["view"]:
        raise ScenePairError("PAIR_CAMERA_VIEW_MISMATCH",
                             {"original":original["view"],"candidate":candidate["view"]})
    return {
      "schema":"OpenRemaster.ZVisionPanoramicScenePairContract.v1",
      "status":"SCENE_AND_CAMERA_PAIRING_TECHNICAL_PASS_GAMEPLAY_FIDELITY_HOLD",
      "game":original["game"],"scene":original["scene"],"view":original["view"],
      "orientation_period":1440,
      "hashes_verified":True,
      "original_capture_sha256":original["capture_sha256"],
      "candidate_capture_sha256":candidate["capture_sha256"],
      "original_pose_evidence_sha256":original["identity_provenance_sha256"],
      "candidate_pose_evidence_sha256":candidate["identity_provenance_sha256"],
      "audio_match":"NOT_TESTED",
      "game_state_equivalence":"NOT_VERIFIED",
      "replay_equivalence":"NOT_VERIFIED",
      "image_pixel_fidelity":"NOT_ATTESTED_BY_SCENE_PAIRING",
      "fidelity_verified":False
    }
