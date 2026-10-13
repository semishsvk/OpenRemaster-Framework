"""Synthetic cross-game positive and negative fixtures; never retail fidelity evidence."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from alignment import evaluate_alignment, admissibility
from semantics import normalize_resource_path, resolve_resources, validate_population
from causal import analyze_causes, promotion_readiness

H = lambda c: c * 64


class AlignmentFixtures(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = Path(self.tmp.name)
        self.orig, self.rec = p / "oracle", p / "reconstruction"
        self.orig.mkdir()
        self.rec.mkdir()
        data = b"SYNTHETIC_FRAME_ONLY_NO_GAME_FIDELITY"
        for root in (self.orig, self.rec):
            (root / "frame.bin").write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        (p / "policy.bin").write_bytes(b"SYNTHETIC_GAME_SPECIFIC_ALIGNMENT_POLICY")
        policy_sha = hashlib.sha256(b"SYNTHETIC_GAME_SPECIFIC_ALIGNMENT_POLICY").hexdigest()
        record = dict(game="OpenZork", scenario_id="TEMPLE_REPLAY",
                      canonical_scene_id="TEMPLE_APPROACH",
                      capture_point_id="frame_001", replay_id="Replay001",
                      input_trace_sha256=H("a"), source_corpus_sha256=H("b"),
                      runtime_fingerprint_sha256=H("c"), tick=60,
                      capture_method="LOCAL_RUNTIME_FILE",
                      remote_desktop_capture_authority=False,
                      camera={"position": [1.0, 2.0, 3.0], "yaw_deg": 359.99,
                              "pitch_deg": 0.0, "fov_deg": 65.0,
                              "viewport": [640, 480], "projection": "PERSPECTIVE",
                              "canonical_space_sha256": H("d")},
                      frame={"relative_path": "frame.bin", "sha256": digest})
        self.bundle = {
            "schema": "OracleAlignmentContract.v1",
            "original": dict(copy.deepcopy(record), oracle_level="ALIGNED_ORACLE"),
            "reconstruction": copy.deepcopy(record),
            "policy": {"status": "GAME_SPECIFIC_VALIDATED", "evidence_sha256": policy_sha,
                       "evidence_path": "policy.bin",
                       "camera_position_tolerance": 0.01, "angle_deg_tolerance": 0.05,
                       "fov_deg_tolerance": 0.001, "tick_tolerance": 0}}
        self.roots = {"original": self.orig, "reconstruction": self.rec, "policy": p}

    def test_identical_scene_admissible(self):
        self.assertEqual(admissibility(self.bundle, self.roots)["status"], "ADMISSIBLE")

    def test_yaw_wraparound(self):
        self.bundle["reconstruction"]["camera"]["yaw_deg"] = 0.01
        self.assertEqual(evaluate_alignment(self.bundle, self.roots)["status"], "ALIGNED")

    def test_different_scene_rejected(self):
        self.bundle["reconstruction"]["canonical_scene_id"] = "COURTYARD_GRILLE"
        result = evaluate_alignment(self.bundle, self.roots)
        self.assertEqual(result["status"], "ALIGNMENT_BLOCKED")
        self.assertIn("IDENTITY_CANONICAL_SCENE_ID_MISMATCH", result["mismatches"])

    def test_wrong_yaw_rejected(self):
        self.bundle["reconstruction"]["camera"]["yaw_deg"] = 25
        self.assertEqual(admissibility(self.bundle, self.roots)["status"], "BLOCKED")

    def test_wrong_fov_rejected(self):
        self.bundle["reconstruction"]["camera"]["fov_deg"] = 75
        self.assertEqual(evaluate_alignment(self.bundle, self.roots)["status"], "ALIGNMENT_BLOCKED")

    def test_wrong_tick_rejected(self):
        self.bundle["reconstruction"]["tick"] = 61
        self.assertEqual(evaluate_alignment(self.bundle, self.roots)["status"], "ALIGNMENT_BLOCKED")

    def test_missing_oracle_provenance_rejected(self):
        self.bundle["original"]["oracle_level"] = "DIAGNOSTIC_CAPTURE"
        self.assertEqual(evaluate_alignment(self.bundle, self.roots)["status"], "INSUFFICIENT_EVIDENCE")

    def test_no_capture_roots_fail_closed(self):
        self.assertEqual(admissibility(self.bundle)["status"], "BLOCKED")

    def test_tampered_policy_provenance_rejected(self):
        (self.roots["policy"] / "policy.bin").write_bytes(b"UNAUTHORIZED_POLICY_MUTATION")
        r = evaluate_alignment(self.bundle, self.roots)
        self.assertEqual(r["status"], "INSUFFICIENT_EVIDENCE")
        self.assertIn("ALIGNMENT_POLICY_EVIDENCE_INVALID", r["missing"])

    def test_tampered_frame_hash_rejected(self):
        (self.rec / "frame.bin").write_bytes(b"TAMPERED")
        self.assertEqual(evaluate_alignment(self.bundle, self.roots)["status"], "INSUFFICIENT_EVIDENCE")

    def test_rdc_stream_not_authority(self):
        self.bundle["original"]["capture_method"] = "RDC_STREAM"
        self.assertEqual(evaluate_alignment(self.bundle, self.roots)["status"], "INSUFFICIENT_EVIDENCE")

    def test_state_delta_remains_measurable(self):
        self.bundle["original"]["observed_state_sha256"] = H("1")
        self.bundle["reconstruction"]["observed_state_sha256"] = H("2")
        self.assertEqual(evaluate_alignment(self.bundle, self.roots)["status"], "ALIGNED")

    def test_real_r27_checkpoint_rejects_unaligned_views(self):
        path = Path(r"F:\Remaster Framework\output\projects\OpenZork\evidence\20261009-R10-VISUAL-DIFF-r27\R27_ALIGNMENT_BLOCKER.json")
        self.assertTrue(path.is_file(), "real R27 evidence file missing")
        evidence = json.loads(path.read_text(encoding="utf-8-sig"))
        self.assertFalse(evidence["godot_scene_view_match_original"])
        self.assertEqual(evidence["pixel_diff"], "NOT_VALID_UNTIL_ALIGNMENT")
        self.bundle["reconstruction"]["canonical_scene_id"] = evidence["godot_states"][0]
        self.assertEqual(evaluate_alignment(self.bundle, self.roots)["status"], "ALIGNMENT_BLOCKED")


class SemanticFixtures(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "provenance.bin").write_bytes(b"SYNTHETIC_ORACLE_METADATA")
        hashvalue = hashlib.sha256(b"SYNTHETIC_ORACLE_METADATA").hexdigest()
        self.resources = {
            "schema": "ResourceResolutionContract.v1", "game": "OpenFallout2",
            "resolution_order": ["loose", "patch", "master"],
            "order_evidence_state": "VALIDATED", "order_evidence_path": "provenance.bin",
            "order_evidence_sha256": hashvalue,
            "layers": [
                {"id": "loose", "source_sha256": H("1"), "entries": []},
                {"id": "patch", "source_sha256": H("2"),
                 "entries": [{"path": r"Scripts\X.INT", "size": 18, "sha256": H("3")}]},
                {"id": "master", "source_sha256": H("4"),
                 "entries": [{"path": "scripts/x.int", "size": 16, "sha256": H("5")}]}
            ]}
        self.population = {
            "schema": "SemanticPopulationGuard.v1",
            "definitions": [{"id": "npc_def", "kind": "NPC"}],
            "instances": [
                {"id": "npcA", "definition_id": "npc_def", "parent_instance_id": None, "active": True},
                {"id": "npcB", "definition_id": "npc_def", "parent_instance_id": "npcA", "active": True}],
            "expectations": {"status": "CORPUS_AND_RUNTIME_VERIFIED",
                             "evidence_path": "provenance.bin", "evidence_sha256": hashvalue,
                             "active_by_kind": {"NPC": {"min": 2, "max": 2}}}
        }

    def test_resource_override_verified_with_evidence(self):
        x = resolve_resources(self.resources, ["SCRIPTS/x.int"], self.root)
        self.assertEqual(x["status"], "RESOLUTION_CONTRACT_PASS")
        self.assertEqual(x["resolved"][0]["winner"]["layer"], "patch")
        self.assertEqual(len(x["resolved"][0]["candidates_in_precedence_order"]), 2)

    def test_resource_override_no_provenance_hold(self):
        self.assertEqual(resolve_resources(self.resources, ["scripts/x.int"])["status"], "STRUCTURAL_ONLY")

    def test_ambiguous_layer_fails(self):
        self.resources["layers"][1]["entries"].append(
            {"path": "scripts/X.int", "size": 999, "sha256": H("9")})
        self.assertEqual(resolve_resources(self.resources, ["scripts/x.int"], self.root)["status"], "BLOCKED")

    def test_resource_missing(self):
        self.assertEqual(resolve_resources(self.resources, ["scripts/missing.int"], self.root)["status"], "BLOCKED")

    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            normalize_resource_path("../../source/MASTER.DAT")

    def test_population_repeated_definition_is_two_instances(self):
        r = validate_population(self.population, self.root)
        self.assertEqual(r["status"], "POPULATION_CONTRACT_PASS")
        self.assertEqual(r["counts"]["active_instances"], 2)
        self.assertEqual(r["counts"]["definitions"], 1)

    def test_population_orphan_parent_rejected(self):
        self.population["instances"][1]["parent_instance_id"] = "unknown"
        self.assertEqual(validate_population(self.population, self.root)["status"], "FAIL")

    def test_population_cycle_rejected(self):
        self.population["instances"][0]["parent_instance_id"] = "npcB"
        self.assertEqual(validate_population(self.population, self.root)["status"], "FAIL")

    def test_population_mismatch_rejected(self):
        self.population["expectations"]["active_by_kind"]["NPC"] = {"min": 3, "max": 3}
        self.assertEqual(validate_population(self.population, self.root)["status"], "FAIL")

    def test_population_no_oracle_proof_hold(self):
        self.assertEqual(validate_population(self.population)["status"], "STRUCTURAL_PASS_SEMANTIC_HOLD")


class CausalFixtures(AlignmentFixtures):
    def test_controlled_improvement_supported_not_fidelity_pass(self):
        a = admissibility(self.bundle, self.roots)
        result = analyze_causes(a, [{"layer": "uv", "mechanism": "winding order",
            "source_mechanism_sha256": H("1"), "oracle_frame_sha256": H("2"),
            "candidate_frame_sha256": H("3"), "comparison_evidence_sha256": H("4"),
            "controlled_intervention": True, "independent_repeat": True,
            "error_before": 42.5, "error_after": 19.25}])
        self.assertEqual(result["findings"][0]["status"], "SUPPORTED_CAUSE")
        self.assertFalse(result["fidelity_verified"])

    def test_without_intervention_stays_hypothesis(self):
        a = admissibility(self.bundle, self.roots)
        result = analyze_causes(a, [{"layer": "lighting", "mechanism": "unverified"}])
        self.assertEqual(result["findings"][0]["status"], "HYPOTHESIS")

    def test_causal_diff_blocked_when_unaligned(self):
        self.bundle["reconstruction"]["canonical_scene_id"] = "BAD"
        result = analyze_causes(admissibility(self.bundle, self.roots), [])
        self.assertEqual(result["status"], "ALIGNMENT_BLOCKED")

    def test_comparator_cannot_self_promote(self):
        a = admissibility(self.bundle, self.roots)
        out = promotion_readiness(a, {"status": "PASS"})
        self.assertEqual(out["status"], "INSUFFICIENT_COMPARATOR")
        self.assertFalse(out["fidelity_verified"])

    def test_comparator_forged_frame_identity_rejected(self):
        a = admissibility(self.bundle, self.roots)
        x = {"schema": "IndependentFidelityComparison.v1", "status": "FAIL",
             "independent_reverification": True, "all_required_layers_covered": True,
             "source_capture_sha256": H("1"), "candidate_capture_sha256": H("2"),
             "comparator_attestation_sha256": H("3"), "runtime_replay_sha256": H("4")}
        self.assertEqual(promotion_readiness(a, x)["status"], "INSUFFICIENT_COMPARATOR")

    def test_comparator_attestation_still_requires_external_acceptance(self):
        a = admissibility(self.bundle, self.roots)
        x = {"schema": "IndependentFidelityComparison.v1", "status": "PASS",
             "independent_reverification": True, "all_required_layers_covered": True,
             "source_capture_sha256": a["source_capture_sha256"],
             "candidate_capture_sha256": a["candidate_capture_sha256"],
             "comparator_attestation_sha256": H("3"), "runtime_replay_sha256": H("4")}
        r = promotion_readiness(a, x)
        self.assertEqual(r["status"], "ELIGIBLE_FOR_EXTERNAL_ACCEPTANCE")
        self.assertFalse(r["fidelity_verified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
