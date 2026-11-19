"""CLI process integration fixtures."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_contracts import AlignmentFixtures

HERE = Path(__file__).resolve().parent


class CLITests(unittest.TestCase):
    def setUp(self):
        self.fixture = AlignmentFixtures("test_identical_scene_admissible")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.manifest = Path(self.fixture.tmp.name) / "oracle_alignment.json"
        self.manifest.write_text(json.dumps(self.fixture.bundle), encoding="utf-8")

    def cmd(self, args):
        return subprocess.run([sys.executable, str(HERE / "gate_cli.py")] + args,
                              capture_output=True, text=True, timeout=10)

    def roots(self):
        d = self.fixture.roots
        return ["--original-root", str(d["original"]),
                "--reconstruction-root", str(d["reconstruction"]),
                "--policy-root", str(d["policy"])]

    def test_cli_aligned_admissible_without_fidelity_promotion(self):
        p = self.cmd(["alignment", str(self.manifest)] + self.roots())
        self.assertEqual(p.returncode, 0, p.stderr)
        j = json.loads(p.stdout)
        self.assertEqual(j["status"], "ADMISSIBLE")
        self.assertFalse(j["fidelity_verified"])

    def test_cli_wrong_scene_exits_nonzero(self):
        self.fixture.bundle["reconstruction"]["canonical_scene_id"] = "DIFFERENT"
        self.manifest.write_text(json.dumps(self.fixture.bundle), encoding="utf-8")
        p = self.cmd(["alignment", str(self.manifest)] + self.roots())
        self.assertEqual(p.returncode, 2)
        self.assertEqual(json.loads(p.stdout)["reason"], "ALIGNMENT_BLOCKED")

    def test_cli_missing_roots_exits_nonzero(self):
        p = self.cmd(["alignment", str(self.manifest)])
        self.assertEqual(p.returncode, 2)

    def test_cli_fallout2_hypothesis_exits_nonzero(self):
        p = self.cmd(["resources", str(HERE / "fixtures" / "fallout2_resource_hypothesis.json"),
                      "--evidence-root", str(HERE / "evidence")])
        self.assertEqual(p.returncode, 2)
        self.assertEqual(json.loads(p.stdout)["status"], "STRUCTURAL_ONLY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
