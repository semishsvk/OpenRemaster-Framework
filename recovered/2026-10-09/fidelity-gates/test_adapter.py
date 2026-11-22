"""ORCH-K003 non-invasive validator integration negative and positive gates."""
import json
from pathlib import Path
import tempfile
import unittest

from alignment import hash_file
from orch_adapter import gated_validate
from test_contracts import AlignmentFixtures


def base_pass(job, result_path):
    return {"schema": "ORCH-K003.ValidationResult.v1", "status": "PASS",
            "failures": [], "worker_result_sha256": "synthetic_base_validation"}


def base_fail(job, result_path):
    return {"schema": "ORCH-K003.ValidationResult.v1", "status": "FAIL",
            "failures": ["EXIT_CODE_MISMATCH"]}


class AdapterFixtures(AlignmentFixtures):
    def make_job(self, kind="fidelity_runtime", aligned=True):
        out = Path(self.tmp.name) / "result"
        out.mkdir(exist_ok=True)
        receipt = out / "result.json"
        receipt.write_text('{"status":"PASS"}', encoding="utf-8")
        if not aligned:
            self.bundle["reconstruction"]["canonical_scene_id"] = "DIFFERENT_SCENE"
        bundle_path = out / "oracle_alignment.json"
        bundle_path.write_text(json.dumps(self.bundle), encoding="utf-8")
        validation = {"oracle_alignment": {
            "manifest_name": bundle_path.name,
            "manifest_sha256": hash_file(bundle_path),
            "roots": {key: str(value) for key, value in self.roots.items()}}}
        return {"execution": {"kind": kind}, "validation": validation}, receipt

    def test_fidelity_missing_alignment_rejected(self):
        job = {"execution": {"kind": "fidelity_runtime"}, "validation": {}}
        result = gated_validate(job, Path(self.tmp.name) / "result.json", base_pass)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("ORACLE_ALIGNMENT_EVIDENCE_MISSING", result["failures"])

    def test_fidelity_aligned_opt_in_pass_without_promotion(self):
        job, receipt = self.make_job()
        result = gated_validate(job, receipt, base_pass)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["oracle_admissibility"]["status"], "ADMISSIBLE")
        self.assertFalse(result["fidelity_verified"])

    def test_fidelity_misaligned_rejected(self):
        job, receipt = self.make_job(aligned=False)
        result = gated_validate(job, receipt, base_pass)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("ORACLE_ALIGNMENT_ALIGNMENT_BLOCKED", result["failures"])

    def test_fidelity_manifest_tamper_rejected(self):
        job, receipt = self.make_job()
        (receipt.parent / "oracle_alignment.json").write_text('{"tampered":true}', encoding="utf-8")
        result = gated_validate(job, receipt, base_pass)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("ORACLE_ALIGNMENT_INDEPENDENT_CHECK_FAILED", result["failures"])

    def test_legacy_fail_must_remain_fail(self):
        job, receipt = self.make_job()
        result = gated_validate(job, receipt, base_fail)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["failures"], ["EXIT_CODE_MISMATCH"])

    def test_ordinary_godot_job_unchanged(self):
        job = {"execution": {"kind": "godot_runtime"}, "validation": {}}
        result = gated_validate(job, Path(self.tmp.name) / "result.json", base_pass)
        self.assertEqual(result["status"], "PASS")
        self.assertNotIn("oracle_admissibility", result)

    def test_explicit_alignment_required_for_non_fidelity_job(self):
        job = {"execution": {"kind": "godot_runtime"},
               "validation": {"require_scene_alignment": True}}
        result = gated_validate(job, Path(self.tmp.name) / "result.json", base_pass)
        self.assertEqual(result["status"], "FAIL")

    def test_replay_diff_requires_failure_not_pass(self):
        job, receipt = self.make_job()
        a = {"source_capture_sha256": self.bundle["original"]["frame"]["sha256"],
             "candidate_capture_sha256": self.bundle["reconstruction"]["frame"]["sha256"],
             "comparator_attestation_sha256": "f" * 64, "runtime_replay_sha256": "e" * 64,
             "schema": "IndependentFidelityComparison.v1", "status": "FAIL",
             "independent_reverification": True}
        job["validation"]["oracle_alignment"]["independent_comparison"] = a
        result = gated_validate(job, receipt, base_pass)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("FIDELITY_COMPARISON_DIFFERENCE", result["failures"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
