"""Exercise review binding with disposable Git source snapshots, never builds."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

STUDIO = Path(__file__).parents[1].resolve()
spec = importlib.util.spec_from_file_location('controls_review', STUDIO / 'tools/verify_controls_review.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class ControlsReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for name in review.source_files(STUDIO):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(STUDIO / name, target)
        files = review.source_files(self.root)
        self.record = self.root / 'tools/controls-review.json'
        self.record.write_text(json.dumps({
            'schema': 'OpenRemaster.StudioControlsReview.v1', 'decision': 'SOURCE_CONTROLS_VERIFIED', 'scope': 'SOURCE_CONTROLS_ONLY',
            'reviewer': 'Synthetic controls reviewer', 'reviewed_at': datetime.now(timezone.utc).date().isoformat(),
            'hash_method': 'SHA256_TEXT_LF_BINARY_RAW', 'source_fingerprint': review.fingerprint(files),
            'files': files, 'production_go': False,
        }))
        self.git('init', '-q')
        self.head = self.commit()

    def git(self, *args):
        return subprocess.check_output(['git', '-c', 'core.autocrlf=false', '-c', 'user.name=ReviewFixture',
            '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false', *args], cwd=self.root, stderr=subprocess.STDOUT, text=True).strip()

    def commit(self):
        self.git('add', '--all')
        self.git('commit', '-q', '-m', 'Synthetic source-review fixture')
        return self.git('rev-parse', 'HEAD')

    def test_exact_reviewed_source_binds_the_actual_package_commit(self):
        value = review.verify(self.root, self.head)
        self.assertEqual(value['source_commit'], self.head)
        self.assertEqual(value['scope'], 'SOURCE_CONTROLS_ONLY')
        self.assertFalse(value['production_go'])
        with self.assertRaisesRegex(ValueError, 'differs'):
            review.verify(self.root, '0' * 40)

    def test_changed_or_added_source_requires_a_new_controls_review(self):
        source = self.root / 'src/DevWorkerPanel.tsx'
        source.write_text(source.read_text() + '\n// Changed synthetic fixture\n')
        with self.assertRaisesRegex(ValueError, 'outside the declared commit'):
            review.verify(self.root, self.head)
        self.head = self.commit()
        with self.assertRaisesRegex(ValueError, 'Source changed since controls review'):
            review.verify(self.root, self.head)

    def test_new_source_census_and_missing_review_do_not_auto_verify(self):
        (self.root / 'src/NewFixture.ts').write_text('export const fixture = true;')
        self.head = self.commit()
        with self.assertRaisesRegex(ValueError, 'Source changed since controls review'):
            review.verify(self.root, self.head)
        self.record.unlink()
        self.head = self.commit()
        with self.assertRaises(FileNotFoundError):
            review.verify(self.root, self.head)


if __name__ == '__main__':
    unittest.main()
