"""Actual local source-report regression tests, no gameplay/fidelity promotion."""
import json
from pathlib import Path
import unittest

from alignment import hash_file
from semantics import resolve_resources

HERE = Path(__file__).resolve().parent


class RealEvidenceChecks(unittest.TestCase):
    def test_fallout2_real_dat_overlap_no_guessed_precedence(self):
        proof = json.loads((HERE / "evidence" / "fallout2_resource_overlap.json").read_text())
        candidate = json.loads((HERE / "fixtures" / "fallout2_resource_hypothesis.json").read_text())
        self.assertEqual(proof["archive_sha256"]["master"].lower(),
                         "9b096d3035edafd4077deeb8ee7877a803b9db98497aa4596624b5c058a84711")
        self.assertEqual(proof["directory_entries"], {"master": 23140, "patch": 489})
        self.assertGreater(proof["overlapping_paths"], 0)
        r = resolve_resources(candidate, candidate["requested"], HERE / "evidence")
        self.assertEqual(r["status"], "STRUCTURAL_ONLY")

    def test_mdk_renderer_not_promoted_from_structural(self):
        p = Path(r"F:\Remaster Framework\work\OpenMDK1\evidence\level3_renderer_binding_checkpoint_v3.json")
        doc = json.loads(p.read_text(encoding="utf-8-sig"))
        self.assertEqual(doc["geometry"]["triangles_total"], 7205)
        self.assertEqual(doc["textures"]["triangles_texture_bound"] +
                         doc["textures"]["hmo7_special_triangles"], 7205)
        self.assertEqual(doc["promotion_gate"]["current"], "RUNTIME_BINDING_BLOCKED")

    def test_ultima9_physical_pages_not_equal_materialized_entities(self):
        p = Path(r"F:\Remaster Framework\work\OpenUltima9\patch-re-001\diffs\nonfixed-page-reachability.json")
        doc = json.loads(p.read_text(encoding="utf-8-sig"))
        record = doc["9"]
        self.assertEqual(record["physical_pages"], 424)
        self.assertEqual(record["reachable_pages"], 353)
        self.assertEqual(record["unreachable_pages"], 71)
        self.assertEqual(record["invalid_next_links"], [])
        self.assertNotEqual(record["physical_pages"], record["reachable_pages"])

    def test_all_five_versioned_schemas_materialized(self):
        expected = ("OracleAlignmentContract.v1", "ComparisonAdmissibilityGuard.v1",
                    "CausalFidelityDiff.v1", "ResourceResolutionContract.v1",
                    "SemanticPopulationGuard.v1")
        for ident in expected:
            with self.subTest(contract=ident):
                path = HERE / "schemas" / (ident + ".schema.json")
                schema = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(schema["$id"], "urn:openremaster:" + ident)
                self.assertEqual(schema["$schema"],
                                 "https://json-schema.org/draft/2020-12/schema")


if __name__ == "__main__":
    unittest.main(verbosity=2)
