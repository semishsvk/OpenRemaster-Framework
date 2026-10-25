"""Generate portable draft-2020-12 JSON schemas for the five fidelity contracts.
Runtime SHA checks and reference integrity are additionally enforced by Python.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "schemas"
ROOT.mkdir(exist_ok=True)
SCHEMA_URI = "https://json-schema.org/draft/2020-12/schema"
HEX = {"type": "string", "pattern": "^[0-9a-fA-F]{64}$"}
STRING = {"type": "string", "minLength": 1}
NUM = {"type": "number"}
FRAME = {"type": "object", "required": ["relative_path", "sha256"],
         "properties": {"relative_path": STRING, "sha256": HEX}}
CAMERA = {"type": "object",
          "required": ["position", "yaw_deg", "pitch_deg", "fov_deg",
                       "projection", "viewport", "canonical_space_sha256"],
          "properties": {"position": {"type": "array", "items": NUM, "minItems": 3, "maxItems": 3},
                         "yaw_deg": NUM, "pitch_deg": NUM, "fov_deg": NUM,
                         "projection": STRING, "viewport": {"type": "array",
                           "items": {"type": "integer", "minimum": 1}, "minItems": 2, "maxItems": 2},
                         "canonical_space_sha256": HEX}}
RECORD = {"type": "object", "required": [
              "game", "scenario_id", "canonical_scene_id", "capture_point_id",
              "replay_id", "input_trace_sha256", "source_corpus_sha256",
              "runtime_fingerprint_sha256", "tick", "camera", "capture_method",
              "remote_desktop_capture_authority", "frame"],
          "properties": {
              **{k: STRING for k in ("game", "scenario_id", "canonical_scene_id", "capture_point_id", "replay_id")},
              **{k: HEX for k in ("input_trace_sha256", "source_corpus_sha256", "runtime_fingerprint_sha256")},
              "tick": NUM, "camera": CAMERA, "frame": FRAME,
              "capture_method": {"enum": ["LOCAL_FRAMEBUFFER", "LOCAL_RUNTIME_FILE", "NATIVE_WINDOW_CAPTURE"]},
              "remote_desktop_capture_authority": {"const": False}}}
POLICY = {"type": "object", "required": [
              "status", "evidence_path", "evidence_sha256",
              "camera_position_tolerance", "angle_deg_tolerance", "fov_deg_tolerance", "tick_tolerance"],
          "properties": {"status": {"const": "GAME_SPECIFIC_VALIDATED"},
                         "evidence_path": STRING, "evidence_sha256": HEX,
                         **{k + "_tolerance": {"type": "number", "minimum": 0} for k in
                            ("camera_position", "angle_deg", "fov_deg", "tick")}}}
ASSET = {"type": "object", "required": ["path", "sha256", "size"],
         "properties": {"path": STRING, "sha256": HEX, "size": {"type": "integer", "minimum": 0}}}
DEFINITION = {"type": "object", "required": ["id", "kind"], "properties": {"id": STRING, "kind": STRING}}
INSTANCE = {"type": "object", "required": ["id", "definition_id", "active"],
            "properties": {"id": STRING, "definition_id": STRING, "active": {"type": "boolean"},
                           "parent_instance_id": {"type": ["string", "null"]}}}
OBSERVATION = {"type": "object", "required": ["layer", "mechanism"],
               "properties": {"layer": STRING, "mechanism": STRING,
                              "controlled_intervention": {"type": "boolean"},
                              "independent_repeat": {"type": "boolean"},
                              "error_before": {"type": "number", "minimum": 0},
                              "error_after": {"type": "number", "minimum": 0}}}
SCHEMAS = {
    "OracleAlignmentContract.v1": {
        "required": ["schema", "original", "reconstruction", "policy"],
        "properties": {"schema": {"const": "OracleAlignmentContract.v1"},
                       "original": {**RECORD, "required": RECORD["required"] + ["oracle_level"],
                                    "properties": {**RECORD["properties"],
                                                   "oracle_level": {"enum": ["ALIGNED_ORACLE", "DETERMINISTIC_ORACLE", "FIDELITY_ATTESTED"]}}},
                       "reconstruction": RECORD, "policy": POLICY}},
    "ComparisonAdmissibilityGuard.v1": {
        "required": ["schema", "status", "alignment"],
        "properties": {"schema": {"const": "ComparisonAdmissibilityGuard.v1"},
                       "status": {"enum": ["ADMISSIBLE", "BLOCKED"]},
                       "may_report_fidelity_score": {"type": "boolean"},
                       "fidelity_verified": {"const": False},
                       "alignment": {"type": "object"}}},
    "CausalFidelityDiff.v1": {
        "required": ["admission", "observations"],
        "properties": {"admission": {"type": "object"},
                       "observations": {"type": "array", "items": OBSERVATION}}},
    "ResourceResolutionContract.v1": {
        "required": ["schema", "resolution_order", "order_evidence_state", "order_evidence_path",
                     "order_evidence_sha256", "layers"],
        "properties": {"schema": {"const": "ResourceResolutionContract.v1"},
                       "game": STRING, "resolution_order": {"type": "array", "items": STRING, "uniqueItems": True},
                       "order_evidence_state": {"enum": ["VALIDATED", "HYPOTHESIS"]},
                       "order_evidence_path": STRING, "order_evidence_sha256": HEX,
                       "layers": {"type": "array", "items": {"type": "object",
                                "required": ["id", "source_sha256", "entries"],
                                "properties": {"id": STRING, "source_sha256": HEX,
                                               "entries": {"type": "array", "items": ASSET}}}}}},
    "SemanticPopulationGuard.v1": {
        "required": ["schema", "definitions", "instances", "expectations"],
        "properties": {"schema": {"const": "SemanticPopulationGuard.v1"},
                       "definitions": {"type": "array", "items": DEFINITION},
                       "instances": {"type": "array", "items": INSTANCE},
                       "expectations": {"type": "object", "required": ["status", "evidence_path", "evidence_sha256", "active_by_kind"],
                                        "properties": {"status": {"enum": ["CORPUS_AND_RUNTIME_VERIFIED", "HYPOTHESIS"]},
                                                       "evidence_path": STRING, "evidence_sha256": HEX,
                                                       "active_by_kind": {"type": "object", "additionalProperties": {
                                                           "type": "object", "required": ["min", "max"],
                                                           "properties": {"min": {"type": "integer", "minimum": 0},
                                                                          "max": {"type": "integer", "minimum": 0}}}}}}}}
}
for ident, fields in SCHEMAS.items():
    document = {"$schema": SCHEMA_URI, "$id": f"urn:openremaster:{ident}",
                "title": ident, "type": "object", **fields}
    path = ROOT / (ident + ".schema.json")
    path.write_text(json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"schema": "OpenRemaster.FidelitySchemasBuild.v1",
                  "count": len(SCHEMAS), "files": sorted(x.name for x in ROOT.glob("*.schema.json"))}))
