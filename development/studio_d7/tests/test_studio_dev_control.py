"""Behavioral client tests; never discover or launch historical workers."""
import contextlib
import base64
import gzip
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
import io
import zipfile
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('studio_dev_control', Path(__file__).parents[1] / 'tools/studio_dev_control.py')
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)
OP = 'a' * 32
SCOPE = 'b' * 64


class Host:
    def __init__(self, root):
        self.root, self.locks, self.launches = root, {}, 0

    @contextlib.contextmanager
    def lock(self, name):
        mutex = self.locks.setdefault(name, threading.Lock())
        owned = mutex.acquire(blocking=False)
        try:
            yield owned
        finally:
            if owned:
                mutex.release()

    def health(self):
        return {'healthy': True, 'state': 'IDLE', 'operation_id': None, 'production_go': False}

    def external_status(self, operation, scenario):
        base = {'schema': 'OpenRemaster.DevWorkflowResult.v1', 'operation_id': operation, 'scenario': scenario, 'production_go': False}
        done = self.root / f'host-state/done/{operation}.json'
        if done.exists():
            return json.loads(done.read_text())
        if (self.root / f'host-state/running/{operation}.json').exists():
            return dict(base, state='RUNNING', launch_count=1)
        if (self.root / f'host-state/pending/{operation}.json').exists():
            return dict(base, state='QUEUED', launch_count=0)
        if (self.root / f'host-state/requests/{operation}.json').exists():
            return dict(base, state='HOLD')
        return dict(base, state='NOT_FOUND')

    def submit(self, operation, scenario):
        marker = self.root / f'host-state/requests/{operation}.json'
        if not marker.exists():
            self.launches += 1
            value = {'operation_id': operation, 'scenario': scenario}
            marker.write_text(json.dumps(value))
            (self.root / f'host-state/pending/{operation}.json').write_text(json.dumps(value))
        return self.external_status(operation, scenario)


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        for name in ('state/operations', 'state/studio-intents', 'host-state/requests', 'host-state/pending', 'host-state/running', 'host-state/done'):
            (self.root / name).mkdir(parents=True)
        self.host = Host(self.root)
        self.api = type('Api', (), {'writer': lambda _: self.host.lock('writer.lock')})()
        self.client = control.Control(self.root, self.api, self.host, SCOPE)

    def request(self, action, operation=OP, **fields):
        return dict(action=action, operation_id=operation, scenario=control.SCENARIO, **fields)

    def intent(self, operation=OP):
        (self.root / f'state/studio-intents/{operation}.json').write_text(json.dumps({'operation_id': operation, 'scenario': control.SCENARIO, 'scope': SCOPE}))

    def terminal(self, stopped=True, launches=1):
        stage = self.root / f'state/operations/{OP}'
        stage.mkdir()
        (stage / 'stdout.log').write_bytes(b'full retained log\r\n' * 20000)
        (stage / 'stderr.log').write_bytes(b'compiler error\r\n')
        worker = {'owned_tree_stopped': stopped, 'stdout_sha256': control.file_hash(stage / 'stdout.log'), 'stderr_sha256': control.file_hash(stage / 'stderr.log')}
        result = {'schema': 'OpenRemaster.DevWorkflowResult.v1', 'state': 'HOLD', 'operation_id': OP,
                  'scenario': control.SCENARIO, 'production_go': False, 'launch_count': launches,
                  'ack': {'operation_id': OP}, 'worker': worker, 'commit': None, 'automatic_retry': False}
        with contextlib.closing(sqlite3.connect(self.root / 'state/ledger.sqlite')) as db:
            db.execute('CREATE TABLE operations (id TEXT PRIMARY KEY,scenario TEXT,state TEXT,launches INTEGER,ack TEXT,result TEXT)')
            db.execute('INSERT INTO operations VALUES (?,?,?,?,?,?)', (OP, control.SCENARIO, 'HOLD', launches, json.dumps(result['ack']), json.dumps(result)))
            db.commit()
        (self.root / f'host-state/done/{OP}.json').write_text(json.dumps(result))
        self.intent()
        return stage

    def test_status_is_read_only_and_does_not_issue_receipts_or_logs(self):
        stage = self.terminal()
        before = {str(p): control.file_hash(p) for p in self.root.rglob('*') if p.is_file()}
        for _ in range(3):
            value = self.client.execute(self.request('status'))
            self.assertEqual(value['state'], 'HOLD')
            self.assertLessEqual(len(value['logs']['stdout.log']), 8192)
        self.assertEqual(before, {str(p): control.file_hash(p) for p in self.root.rglob('*') if p.is_file()})
        self.assertFalse((self.root / 'state/dev-receipts').exists())
        self.assertFalse((self.root / 'ipc-logs').exists())

    def test_pre_intent_rejection_is_attempt_bound_and_never_replayed(self):
        self.intent('c' * 32)
        request = self.request('submit', attempt_id='d' * 32)
        value = self.client.execute(request)
        self.assertEqual(value['state'], 'DENIED')
        self.assertEqual(value['not_admitted']['attempt_id'], 'd' * 32)
        self.assertEqual(value['launch_count'], 0)
        self.assertIsNone(self.client.evidence(OP)[0]['files']['intent'])
        self.assertEqual(self.host.launches, 0)
        restarted = control.Control(self.root, self.api, self.host, SCOPE)
        self.assertEqual(restarted.execute(self.request('status'))['not_admitted'], value['not_admitted'])
        resolved = restarted.execute(self.request('resolve', expected_evidence_sha256=value['evidence_sha256'], attempt_id='d'*32, acknowledge=True, reason='Reviewed the rejected fresh attempt.'))
        self.assertTrue(resolved['resolution']['new_operation_allowed'])
        with self.assertRaisesRegex(ValueError, 'CANNOT_BE_RESUBMITTED'):
            restarted.execute(request)

    def test_rejection_proof_requires_absent_intent_queue_and_ledger(self):
        request = self.request('reject', attempt_id='d' * 32, reason='Native receipt rejected before control admission.')
        self.intent()
        with self.assertRaisesRegex(ValueError, 'PROOF_UNAVAILABLE'):
            self.client.execute(request)
        self.assertFalse(self.client.path(f'state/studio-rejections/{OP}.json').exists())
        with patch.object(self.host, 'submit', side_effect=ValueError('host failed after intent')):
            with self.assertRaisesRegex(ValueError, 'after intent'):
                self.client.execute(self.request('submit', attempt_id='d' * 32))
        self.assertNotIn('not_admitted', self.client.execute(self.request('status')))

    def test_native_rejection_rejects_changed_attempt_and_preserves_unknown_ids(self):
        value = self.client.execute(self.request('reject', attempt_id='d' * 32, reason='Native admission unavailable.'))
        self.assertTrue(value['recovery']['allowed'])
        with self.assertRaisesRegex(ValueError, 'CANNOT_BE_REUSED'):
            self.client.execute(self.request('reject', attempt_id='e' * 32, reason='A different attempted reuse.'))
        unknown = self.client.execute(self.request('status', 'f' * 32))
        self.assertFalse(unknown['recovery']['allowed'])

    def test_busy_proof_can_be_verified_later_without_resubmitting(self):
        request = self.request('reject', attempt_id='d'*32, reason='Native admission unavailable.')
        with self.host.lock('writer.lock'):
            with self.assertRaisesRegex(ValueError, 'BUILD_WRITER_BUSY'):
                self.client.execute(request)
        unknown = self.client.execute(self.request('status'))
        self.assertEqual(unknown['state'], 'NOT_FOUND')
        proof_request = self.request('prove_not_admitted', attempt_id='d'*32, expected_evidence_sha256=unknown['evidence_sha256'])
        with self.host.lock('writer.lock'):
            with self.assertRaisesRegex(ValueError, 'BUILD_WRITER_BUSY'):
                self.client.execute(proof_request)
        value = self.client.execute(proof_request)
        self.assertEqual(value['state'], 'DENIED')
        self.assertEqual(self.host.launches, 0)
        for attempt in (None, 'e'*32):
            fields = {'attempt_id': attempt} if attempt else {}
            with self.assertRaisesRegex(ValueError, 'REJECTION_ATTEMPT_MISMATCH'):
                self.client.execute(self.request('resolve', expected_evidence_sha256=value['evidence_sha256'], reason='Reviewed this rejected attempt.', acknowledge=True, **fields))
        with self.assertRaisesRegex(ValueError, 'ATTEMPT_ID_REQUIRED'):
            self.client.execute(self.request('prove_not_admitted', expected_evidence_sha256=unknown['evidence_sha256']))
        self.assertFalse(self.client.path(f'state/studio-resolutions/{OP}.json').exists())

    def test_operation_output_directory_prevents_absence_proof_and_invalidates_old_proof(self):
        value = self.client.execute(self.request('reject', attempt_id='d'*32, reason='Native admission unavailable.'))
        directory = self.client.path(f'state/operations/{OP}')
        directory.mkdir()
        (directory / 'stdout.log').write_text('Unreconciled prior output')
        with self.assertRaisesRegex(ValueError, 'PROOF_UNAVAILABLE'):
            self.client.execute(self.request('reject', attempt_id='d'*32, reason='Do not discard unknown output.'))
        changed = self.client.execute(self.request('status'))
        self.assertNotIn('not_admitted', changed)
        self.assertFalse(changed['recovery']['allowed'])
        self.assertNotEqual(changed['evidence_sha256'], value['evidence_sha256'])

    def test_manifest_and_rejection_receipt_hashes_cover_the_bytes_actually_parsed(self):
        self.terminal()
        value = self.client.execute(self.request('status'))
        archived = self.client.execute(self.request('archive', expected_evidence_sha256=value['evidence_sha256']))
        path = Path(archived['archive']['path']) / 'manifest.json'
        raw = path.read_bytes()
        real_hash = control.file_hash
        def reject_second_manifest_read(file):
            if Path(file) == path:
                raise AssertionError('Manifest checksum must use the parsed snapshot bytes')
            return real_hash(file)
        with patch.object(control, 'file_hash', side_effect=reject_second_manifest_read):
            receipt = self.client.archive_receipt(OP, value['evidence_sha256'])
        self.assertEqual(receipt['manifest_sha256'], control.digest(raw))
        malicious = json.loads(raw)
        malicious['logs'][0]['name'] = '../outside.txt'
        old_receipt = archived['archive']
        def swap_manifest(*args):
            path.write_text(json.dumps(malicious))
            return old_receipt
        with patch.object(self.client, 'archive', side_effect=swap_manifest):
            with self.assertRaisesRegex(ValueError, 'ARCHIVE_PATH_DENIED'):
                self.client.export_logs(OP, value['evidence_sha256'])
        self.assertFalse((path.parent / 'diagnostics.zip').exists())

    def test_archive_pages_and_complete_export_preserve_exact_log_bytes(self):
        stage = self.terminal()
        status = self.client.execute(self.request('status'))
        archived = self.client.execute(self.request('archive', expected_evidence_sha256=status['evidence_sha256']))
        manifest = archived['archive']['manifest_sha256']
        before = {str(p): control.file_hash(p) for p in self.root.rglob('*') if p.is_file()}
        page = self.client.execute(self.request('logs', expected_evidence_sha256=status['evidence_sha256'], source='archive', name='stdout.log', offset=65530, limit=65536, manifest_sha256=manifest))
        self.assertEqual(base64.b64decode(page['bytes_base64']), (stage / 'stdout.log').read_bytes()[65530:131066])
        self.assertTrue(page['verified'])
        self.assertEqual(page['file_sha256'], control.file_hash(stage / 'stdout.log'))
        self.assertEqual(before, {str(p): control.file_hash(p) for p in self.root.rglob('*') if p.is_file()})
        exported = self.client.execute(self.request('export', expected_evidence_sha256=status['evidence_sha256']))
        pieces, offset = [], 0
        while offset < exported['bytes']:
            page = self.client.execute(self.request('logs', expected_evidence_sha256=status['evidence_sha256'], source='bundle', name='diagnostics.zip', offset=offset, limit=100, manifest_sha256=manifest))
            pieces.append(base64.b64decode(page['bytes_base64']))
            offset = page['next_offset']
        raw = b''.join(pieces)
        self.assertEqual(control.digest(raw), exported['sha256'])
        with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
            self.assertEqual(set(bundle.namelist()), {'manifest.json', 'stdout.log.gz', 'stderr.log.gz'})
            self.assertEqual(gzip.decompress(bundle.read('stdout.log.gz')), (stage / 'stdout.log').read_bytes())
        self.assertEqual(self.client.execute(self.request('export', expected_evidence_sha256=status['evidence_sha256'])), exported)
        bundle_path = Path(archived['archive']['path']) / 'diagnostics.zip'
        with zipfile.ZipFile(bundle_path, 'a') as bundle:
            bundle.writestr('unexpected.txt', 'injected')
        with self.assertRaisesRegex(ValueError, 'EXPORT_MEMBERS_CHANGED'):
            self.client.execute(self.request('export', expected_evidence_sha256=status['evidence_sha256']))

    def test_live_log_pages_are_partial_and_never_claim_archive_verification(self):
        stage = self.terminal()
        status = self.client.execute(self.request('status'))
        page = self.client.execute(self.request('logs', expected_evidence_sha256=status['evidence_sha256'], source='live', name='stdout.log', offset=0, limit=12))
        self.assertEqual(base64.b64decode(page['bytes_base64']), (stage / 'stdout.log').read_bytes()[:12])
        self.assertFalse(page['verified'])
        self.assertFalse(page['eof'])
        self.assertIsNone(page['file_sha256'])
        for fields in ({'name':'../ledger.sqlite'}, {'offset':-1}, {'limit':1048577}, {'source':'archive','manifest_sha256':'0'*64}):
            request = self.request('logs', expected_evidence_sha256=status['evidence_sha256'], source='live', name='stdout.log', offset=0, limit=12)
            request.update(fields)
            with self.assertRaises(ValueError):
                self.client.execute(request)

    def test_queued_and_running_do_not_invent_launch_evidence(self):
        value = self.client.execute(self.request('submit'))
        self.assertEqual(value['state'], 'QUEUED')
        self.assertNotIn('launch_count', value)
        pending = self.root / f'host-state/pending/{OP}.json'
        pending.rename(self.root / f'host-state/running/{OP}.json')
        value = self.client.execute(self.request('status'))
        self.assertEqual(value['state'], 'RUNNING')
        self.assertNotIn('launch_count', value)
        self.assertFalse(value['recovery']['allowed'])

    def test_archive_retains_full_bytes_and_all_original_evidence(self):
        stage = self.terminal()
        raw = (stage / 'stdout.log').read_bytes()
        value = self.client.execute(self.request('status'))
        archived = self.client.execute(self.request('archive', expected_evidence_sha256=value['evidence_sha256']))
        archive = Path(archived['archive']['path'])
        self.assertEqual(gzip.decompress((archive / 'stdout.log.gz').read_bytes()), raw)
        self.assertEqual((stage / 'stdout.log').read_bytes(), raw)
        self.assertEqual(archived['state'], 'HOLD')
        self.assertIsNone(archived['resolution'])
        self.assertEqual(self.host.launches, 0)
        again = self.client.execute(self.request('archive', expected_evidence_sha256=value['evidence_sha256']))
        self.assertEqual(again['archive'], archived['archive'])

    def test_explicit_resolution_survives_restart_without_reexecution(self):
        self.terminal()
        value = self.client.execute(self.request('status'))
        request = self.request('resolve', expected_evidence_sha256=value['evidence_sha256'], reason='Reviewed compiler failure; no process remains.', acknowledge=True)
        resolved = self.client.execute(request)
        self.assertEqual(resolved['state'], 'HOLD')
        self.assertEqual(resolved['resolution']['disposition'], 'ACKNOWLEDGED_NO_RETRY')
        self.assertTrue(resolved['resolution']['new_operation_allowed'])
        fresh = control.Control(self.root, self.api, self.host, SCOPE)
        self.assertEqual(fresh.execute(self.request('status'))['resolution'], resolved['resolution'])
        self.assertEqual(fresh.execute(request)['resolution'], resolved['resolution'])
        with self.assertRaisesRegex(ValueError, 'CANNOT_BE_RESUBMITTED'):
            fresh.execute(self.request('submit'))
        self.assertEqual(self.host.launches, 0)
        self.assertEqual(fresh.execute(self.request('submit', 'c' * 32))['state'], 'QUEUED')
        self.assertEqual(self.host.launches, 1)

    def test_unknown_or_unstopped_hold_cannot_be_cleared(self):
        unknown = self.client.execute(self.request('status'))
        self.assertFalse(unknown['recovery']['allowed'])
        self.terminal(stopped=False)
        held = self.client.execute(self.request('status'))
        self.assertFalse(held['recovery']['allowed'])
        with self.assertRaisesRegex(ValueError, 'NOT_PROVEN_SAFE'):
            self.client.execute(self.request('resolve', expected_evidence_sha256=held['evidence_sha256'], reason='Explicit attempted acknowledgment.', acknowledge=True))
        self.assertFalse((self.root / 'state/studio-resolutions').exists())

    def test_stale_evidence_and_missing_acknowledgment_fail_before_writing(self):
        self.terminal()
        held = self.client.execute(self.request('status'))
        for extra, error in [({'expected_evidence_sha256': '0' * 64, 'acknowledge': True}, 'STALE_EVIDENCE'),
                             ({'expected_evidence_sha256': held['evidence_sha256']}, 'ACKNOWLEDGMENT_REQUIRED')]:
            with self.assertRaisesRegex(ValueError, error):
                self.client.execute(self.request('resolve', reason='An explicit diagnostic note.', **extra))
        self.assertFalse((self.root / 'state/studio-resolutions').exists())
        self.assertFalse((self.root / 'state/studio-archives').exists())

    def test_unresolved_intent_blocks_another_window_and_replay_does_not_enqueue_twice(self):
        self.client.execute(self.request('submit'))
        self.client.execute(self.request('submit'))
        self.assertEqual(self.host.launches, 1)
        with self.assertRaisesRegex(ValueError, 'PREVIOUS_STUDIO_OPERATION_UNRESOLVED'):
            control.Control(self.root, self.api, self.host, SCOPE).execute(self.request('submit', 'd' * 32))
        self.assertEqual(self.host.launches, 1)

    def test_unpublished_client_intent_can_be_acknowledged_but_not_retried(self):
        self.intent()
        held = self.client.execute(self.request('status'))
        self.assertTrue(held['recovery']['allowed'])
        resolved = self.client.execute(self.request('resolve', expected_evidence_sha256=held['evidence_sha256'], reason='Confirmed queue publication did not occur.', acknowledge=True))
        self.assertTrue(resolved['resolution']['new_operation_allowed'])
        with self.assertRaisesRegex(ValueError, 'CANNOT_BE_RESUBMITTED'):
            self.client.execute(self.request('submit'))

    def test_active_writer_or_pending_queue_prevents_archiving_and_recovery(self):
        self.terminal()
        held = self.client.execute(self.request('status'))
        with self.host.lock('writer.lock'):
            with self.assertRaisesRegex(ValueError, 'BUILD_WRITER_BUSY'):
                self.client.execute(self.request('archive', expected_evidence_sha256=held['evidence_sha256']))
        (self.root / f'host-state/pending/{OP}.json').write_text(json.dumps({'operation_id': OP, 'scenario': control.SCENARIO}))
        fresh = self.client.execute(self.request('status'))
        self.assertFalse(fresh['recovery']['allowed'])
        with self.assertRaisesRegex(ValueError, 'ACTIVE_LOGS'):
            self.client.execute(self.request('archive', expected_evidence_sha256=fresh['evidence_sha256']))

    def test_capacity_and_tampered_archives_fail_without_deleting_originals(self):
        stage = self.terminal()
        held = self.client.execute(self.request('status'))
        with patch.object(control, 'MAX_ARCHIVES', 0):
            with self.assertRaisesRegex(ValueError, 'CAPACITY'):
                self.client.execute(self.request('archive', expected_evidence_sha256=held['evidence_sha256']))
        archived = self.client.execute(self.request('archive', expected_evidence_sha256=held['evidence_sha256']))
        (Path(archived['archive']['path']) / 'stdout.log.gz').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'ARCHIVE_CONTENT_CHANGED'):
            self.client.execute(self.request('status'))
        self.assertTrue((stage / 'stdout.log').is_file())

    def test_operation_path_escape_duplicate_json_and_wrong_project_are_denied(self):
        for change in [{'operation_id': '../escape'}, {'scenario': 'build_openazrael_dev'}, {'extra': True}]:
            with self.assertRaises(ValueError):
                self.client.execute(dict(self.request('status'), **change))
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_JSON_KEY'):
            control.decode('{"action":"status","action":"submit"}')

    def test_atomic_record_never_publishes_interrupted_or_overwritten_bytes(self):
        target = self.root / f'state/studio-intents/{OP}.json'
        with patch.object(control.os, 'fsync', side_effect=OSError('interrupted write')):
            with self.assertRaises(OSError):
                control.atomic_new(self.root, target, {'operation_id': OP})
        self.assertFalse(target.exists())
        self.assertEqual(list(target.parent.iterdir()), [])
        control.atomic_new(self.root, target, {'original': True})
        with self.assertRaises(FileExistsError):
            control.atomic_new(self.root, target, {'replacement': True})
        self.assertEqual(json.loads(target.read_text()), {'original': True})

    def test_failed_and_killed_archive_copies_do_not_exhaust_capacity(self):
        stage = self.terminal()
        held = self.client.execute(self.request('status'))
        request = self.request('archive', expected_evidence_sha256=held['evidence_sha256'])
        with patch.object(control.gzip, 'GzipFile', side_effect=OSError('archive interrupted')):
            with self.assertRaises(OSError):
                self.client.execute(request)
        parent = self.root / f'state/studio-archives/{OP}'
        self.assertEqual(list(parent.iterdir()), [])
        orphan = parent / ('.partial-' + 'e' * 32)
        orphan.mkdir()
        (orphan / 'stdout.log.gz').write_bytes(b'incomplete compressed copy')
        with patch.object(control, 'MAX_ARCHIVES', 1):
            result = self.client.execute(request)
        self.assertTrue(result['archive'])
        self.assertFalse(orphan.exists())
        self.assertTrue((stage / 'stdout.log').exists())

    def test_submit_checks_terminal_metadata_without_revalidating_old_artifacts(self):
        self.terminal()
        done = self.root / f'host-state/done/{OP}.json'
        result = json.loads(done.read_text())
        result['state'] = 'COMMITTED'
        done.write_text(json.dumps(result))
        with contextlib.closing(sqlite3.connect(self.root / 'state/ledger.sqlite')) as db:
            db.execute('UPDATE operations SET state=?,result=? WHERE id=?', ('COMMITTED', json.dumps(result), OP))
            db.commit()
        external_status = self.host.external_status
        def only_current(operation, scenario):
            self.assertNotEqual(operation, OP, 'Historical artifacts must not be rehashed for admission')
            return external_status(operation, scenario)
        with patch.object(self.host, 'external_status', side_effect=only_current):
            value = self.client.execute(self.request('submit', 'c' * 32, dev_receipt_sha256='f' * 64))
        self.assertEqual(value['state'], 'QUEUED')
        intent = json.loads((self.root / ('state/studio-intents/' + 'c' * 32 + '.json')).read_text())
        self.assertEqual(intent['dev_receipt_sha256'], 'f' * 64)

    def test_unknown_operation_cannot_consume_archive_capacity(self):
        held = self.client.execute(self.request('status'))
        with self.assertRaisesRegex(ValueError, 'KNOWN_OPERATION_REQUIRED'):
            self.client.execute(self.request('archive', expected_evidence_sha256=held['evidence_sha256']))
        self.assertFalse((self.root / 'state/studio-archives').exists())

    def test_scope_matches_native_canonical_config(self):
        config = json.loads((Path(__file__).parents[1] / 'src-tauri/dev-worker-pins.json').read_text())
        actual = control.digest(json.dumps(config, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())
        self.assertEqual(actual, 'c5f58f85ae31f4f9a674ae24a9c3ca9d08b18a01fcee35cb81064c828440d60e')

    def test_symlink_log_is_rejected_without_reading_target(self):
        stage = self.terminal()
        log = stage / 'stdout.log'
        log.unlink()
        try:
            log.symlink_to(self.root / 'state/ledger.sqlite')
        except OSError as error:
            self.skipTest('Environment cannot create a symlink; rejection was not exercised: ' + str(error))
        with self.assertRaisesRegex(ValueError, 'REPARSE_PATH_DENIED'):
            self.client.execute(self.request('status'))


if __name__ == '__main__':
    unittest.main()
