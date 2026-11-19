"""Studio client for the existing pinned HomePC queue; no worker or scheduler.

Status does not issue receipts, enqueue work, or create per-query log files.
Recovery acknowledges a diagnosed terminal hold; it never retries that ID.
Original queue, ledger and operation files are never deleted or rewritten.
"""
import argparse
import base64
import contextlib
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
import uuid
import zipfile

SCENARIO = 'build_studio_dev'
MAX_JSON = 131072
MAX_LOGS = 64 * 1024 * 1024
MAX_ARCHIVES = 64
MAX_RETAINED_BYTES = 256 * 1024 * 1024
TERMINAL = {'COMMITTED', 'HOLD', 'DENIED', 'NOT_FOUND'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw):
    if len(raw) > MAX_JSON:
        raise ValueError('JSON_SIZE')
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('DUPLICATE_JSON_KEY')
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=unique)


def confined(root, path):
    """Reject symlinks/junctions before reading or writing an operation path."""
    path = Path(path)
    if not path.is_absolute() or not path.is_relative_to(root):
        raise ValueError('PATH_OUTSIDE_WORKER')
    for part in [path, *path.parents]:
        if part.exists() or part.is_symlink():
            info = part.lstat()
            if part.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('REPARSE_PATH_DENIED')
        if part == root:
            break
    if not path.resolve().is_relative_to(root):
        raise ValueError('RESOLVED_PATH_OUTSIDE_WORKER')
    return path


def file_hash(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(65536), b''):
            h.update(block)
    return h.hexdigest()


def read_optional(root, path):
    path = confined(root, path)
    if not path.exists():
        return None
    with path.open('rb') as stream:
        raw = stream.read(MAX_JSON + 1)
    if len(raw) > MAX_JSON:
        raise ValueError('JSON_SIZE')
    return decode(raw.decode('utf-8-sig'))


def atomic_new(root, path, value):
    path = confined(root, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical(value)
    if len(raw) > MAX_JSON:
        raise ValueError('RECORD_SIZE')
    # Publish only complete bytes. Windows rename refuses an existing target;
    # POSIX uses an exclusive hard link. A killed writer leaves an unused .tmp.
    temporary = confined(root, path.parent / ('.' + path.name + '-' + uuid.uuid4().hex + '.tmp'))
    try:
        with temporary.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name == 'nt':
            os.rename(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return digest(raw)


def validate_request(value):
    if type(value) is not dict or set(value) - {'action', 'operation_id', 'scenario', 'expected_evidence_sha256', 'reason', 'acknowledge', 'dev_receipt_sha256', 'attempt_id', 'source', 'name', 'offset', 'limit', 'manifest_sha256'}:
        raise ValueError('REQUEST_SCHEMA')
    if value.get('action') not in ('status', 'submit', 'archive', 'resolve', 'capabilities', 'reject', 'logs', 'export'):
        raise ValueError('ACTION_DENIED')
    if value.get('scenario') != SCENARIO or not re.fullmatch('[a-f0-9]{32}', str(value.get('operation_id', ''))):
        raise ValueError('OPERATION_SCOPE')
    if 'dev_receipt_sha256' in value and (value['action'] != 'submit' or not re.fullmatch('[a-f0-9]{64}', str(value['dev_receipt_sha256']))):
        raise ValueError('RECEIPT_SCOPE')
    if 'attempt_id' in value and (value['action'] not in ('submit', 'reject') or not re.fullmatch('[a-f0-9]{32}', str(value['attempt_id']))):
        raise ValueError('ATTEMPT_ID_REQUIRED')
    if value['action'] == 'reject' and ('attempt_id' not in value or not isinstance(value.get('reason'), str) or not 1 <= len(value['reason']) <= 2048):
        raise ValueError('REJECTION_DETAILS_REQUIRED')
    if value['action'] in ('archive', 'resolve', 'logs', 'export'):
        if not re.fullmatch('[a-f0-9]{64}', str(value.get('expected_evidence_sha256', ''))):
            raise ValueError('EXPECTED_EVIDENCE_REQUIRED')
    if value['action'] == 'logs':
        if (value.get('source') not in ('live', 'archive', 'bundle')
                or value.get('name') not in (('diagnostics.zip',) if value.get('source') == 'bundle' else ('stdout.log', 'stderr.log'))
                or type(value.get('offset')) is not int or not 0 <= value['offset'] <= MAX_LOGS + MAX_JSON
                or type(value.get('limit')) is not int or not 1 <= value['limit'] <= 1024 * 1024):
            raise ValueError('LOG_PAGE_SCOPE')
        if value['source'] != 'live' and not re.fullmatch('[a-f0-9]{64}', str(value.get('manifest_sha256', ''))):
            raise ValueError('ARCHIVE_MANIFEST_REQUIRED')
    if value['action'] == 'resolve':
        reason = value.get('reason')
        if value.get('acknowledge') is not True or not isinstance(reason, str) or not 10 <= len(reason.strip()) <= 1024:
            raise ValueError('EXPLICIT_ACKNOWLEDGMENT_REQUIRED')
    return value


class Control:
    def __init__(self, root, api, host, scope):
        self.root, self.api, self.host, self.scope = Path(root).resolve(), api, host, scope

    def path(self, relative):
        return confined(self.root, self.root / relative)

    def ledger(self, operation):
        path = self.path('state/ledger.sqlite')
        if not path.exists():
            return None
        with contextlib.closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1)) as db:
            db.execute('PRAGMA query_only=ON')
            row = db.execute('SELECT id,scenario,state,launches,ack,result FROM operations WHERE id=?', (operation,)).fetchone()
        if row is None:
            return None
        if row[0] != operation or row[1] != SCENARIO:
            raise ValueError('LEDGER_OPERATION_CONFLICT')
        return {'operation_id': row[0], 'scenario': row[1], 'state': row[2], 'launch_count': row[3],
                'ack': decode(row[4]), 'result': decode(row[5]) if row[5] is not None else None}

    def evidence(self, operation):
        files = {}
        for label, relative in [
            ('request', f'host-state/requests/{operation}.json'),
            ('pending', f'host-state/pending/{operation}.json'),
            ('running', f'host-state/running/{operation}.json'),
            ('done', f'host-state/done/{operation}.json'),
            ('launch', f'state/operations/{operation}/launch.json'),
            ('intent', f'state/studio-intents/{operation}.json'),
        ]:
            files[label] = read_optional(self.root, self.path(relative))
        for value in files.values():
            if value is not None and (value.get('operation_id') != operation or value.get('scenario', SCENARIO) != SCENARIO):
                raise ValueError('OPERATION_FILE_CONFLICT')
            if value is not None and (value.get('production_go', False) is not False or value.get('independent_authority', False) is not False):
                raise ValueError('OPERATION_FILE_AUTHORITY')
        if files['intent'] is not None and files['intent'].get('scope') != self.scope:
            raise ValueError('INTENT_SCOPE_CHANGED')
        rejection = read_optional(self.root, self.path(f'state/studio-rejections/{operation}.json'))
        if rejection is not None:
            if (rejection.get('schema') != 'OpenRemaster.NotAdmitted.v1' or rejection.get('operation_id') != operation
                    or rejection.get('scope') != self.scope or rejection.get('production_go') is not False
                    or not re.fullmatch('[a-f0-9]{32}', str(rejection.get('attempt_id', '')))):
                raise ValueError('REJECTION_SCOPE_CHANGED')
            # Do not change the evidence digest of pre-existing operations.
            files['rejection'] = rejection
        core = {'operation_id': operation, 'scenario': SCENARIO, 'scope': self.scope, 'files': files, 'ledger': self.ledger(operation)}
        return core, digest(canonical(core))

    def eligible(self, core, result):
        files, row = core['files'], core['ledger']
        health = self.host.health()
        if files['pending'] is not None or files['running'] is not None or health.get('operation_id') == core['operation_id']:
            return False, 'Queued or running work must be reconciled by its worker owner.'
        if result['state'] not in {'HOLD', 'DENIED', 'NOT_FOUND'}:
            return False, 'Only a diagnosed held or unlaunched operation can be acknowledged.'
        if files.get('rejection') is not None and row is None and all(value is None for key, value in files.items() if key != 'rejection'):
            return True, 'This attempt was rejected before admission; no intent, queue, ledger or launch exists.'
        if row is not None:
            if row['state'] != 'HOLD' or row['result'] is None:
                return False, 'The ledger has no terminal held result.'
            worker = row['result'].get('worker', {})
            if row['launch_count'] == 1 and worker.get('owned_tree_stopped') is not True:
                return False, 'Stopped owned-process evidence is missing; the outcome stays on hold.'
            if row['launch_count'] not in (0, 1):
                return False, 'Launch evidence is invalid.'
            if row['launch_count'] == 0 and files['launch'] is not None:
                return False, 'Launch records contradict the zero-launch ledger.'
            if files['done'] != row['result']:
                return False, 'Queue and ledger results need reconciliation.'
            return True, 'Terminal ledger evidence confirms no owned build remains active.'
        if files['intent'] is not None and files['launch'] is None and files['request'] is None and files['done'] is None:
            return True, 'This client recorded an intent, but the queue never published the request.'
        return False, 'Unknown or imported operations cannot be cleared without worker evidence.'

    def base_result(self, operation):
        self.evidence(operation)
        progress = read_optional(self.root, self.path(f'state/operations/{operation}/build-progress.json'))
        if progress is not None and progress.get('operation_id') != operation:
            raise ValueError('PROGRESS_OPERATION_CONFLICT')
        raw = self.host.external_status(operation, SCENARIO)
        if raw.get('schema') != 'OpenRemaster.DevWorkflowResult.v1' or raw.get('operation_id') != operation or raw.get('production_go') is not False:
            raise ValueError('HOST_RESPONSE_SCOPE')
        if raw.get('independent_authority', False) is not False or raw.get('engine', 'unsigned-studio-dev-build') != 'unsigned-studio-dev-build':
            raise ValueError('HOST_RESPONSE_AUTHORITY')
        if raw.get('profile', 'DEV_UNSIGNED') != 'DEV_UNSIGNED':
            raise ValueError('HOST_PROFILE_DENIED')
        result = dict(raw, schema='OpenRemaster.DevWorkflowResult.v2', independent_authority=False,
                      engine='unsigned-studio-dev-build', control_scope=self.scope, control_verified=True, automatic_retry=False)
        # A claimed queue file is not proof of a compiler launch. Use the ledger.
        row = self.ledger(operation)
        if result['state'] not in {'REQUESTED', 'QUEUED', 'RUNNING', 'ACKNOWLEDGED', 'STARTED', 'COMMITTED', 'HOLD', 'DENIED', 'BUSY', 'NOT_FOUND'}:
            raise ValueError('HOST_STATE_DENIED')
        if result['state'] in ('QUEUED', 'RUNNING'):
            result.pop('launch_count', None)
            if row is not None:
                result['launch_count'] = row['launch_count']
        return result

    def resolution(self, operation, evidence_sha, verify_content=True):
        receipt = read_optional(self.root, self.path(f'state/studio-resolutions/{operation}.json'))
        if receipt is None:
            return None
        if (receipt.get('schema') != 'OpenRemaster.DevHoldResolution.v1' or receipt.get('operation_id') != operation
                or receipt.get('scope') != self.scope or receipt.get('evidence_sha256') != evidence_sha
                or receipt.get('disposition') != 'ACKNOWLEDGED_NO_RETRY' or receipt.get('production_go') is not False):
            raise ValueError('RESOLUTION_EVIDENCE_CHANGED')
        archive = self.archive_receipt(operation, evidence_sha, verify_content)
        if archive is None or archive['manifest_sha256'] != receipt.get('archive_manifest_sha256'):
            raise ValueError('RESOLUTION_ARCHIVE_CHANGED')
        return dict(receipt, record_sha256=file_hash(self.path(f'state/studio-resolutions/{operation}.json')), new_operation_allowed=True)

    def status(self, operation):
        result = self.base_result(operation)
        core, sha = self.evidence(operation)
        rejection = core['files'].get('rejection')
        if rejection is not None and core['ledger'] is None and all(value is None for key, value in core['files'].items() if key != 'rejection'):
            result.update(state='DENIED', launch_count=0, reason=rejection['reason'], not_admitted=dict(rejection, record_sha256=file_hash(self.path(f'state/studio-rejections/{operation}.json'))))
        allowed, reason = self.eligible(core, result)
        result['evidence_sha256'] = sha
        result['recovery'] = {'allowed': allowed, 'reason': reason}
        result['resolution'] = self.resolution(operation, sha)
        result['archive'] = self.archive_receipt(operation, sha)
        result['logs'] = {}
        for name in ('stdout.log', 'stderr.log'):
            path = self.path(f'state/operations/{operation}/{name}')
            if path.exists():
                with path.open('rb') as stream:
                    stream.seek(max(0, path.stat().st_size - 8192))
                    result['logs'][name] = stream.read(8192).decode('utf-8', errors='replace')
        return result

    def archive_receipt(self, operation, evidence_sha, verify_content=True):
        directory = self.path(f'state/studio-archives/{operation}/{evidence_sha}')
        manifest = read_optional(self.root, directory / 'manifest.json')
        if manifest is None:
            return None
        if (manifest.get('schema') != 'OpenRemaster.DevLogArchive.v1' or manifest.get('production_go') is not False
                or manifest.get('operation_id') != operation or manifest.get('evidence_sha256') != evidence_sha or manifest.get('scope') != self.scope
                or not isinstance(manifest.get('logs'), list) or len(manifest['logs']) > 2):
            raise ValueError('ARCHIVE_SCOPE_CHANGED')
        names = set()
        for item in manifest['logs']:
            if item['name'] not in ('stdout.log.gz', 'stderr.log.gz') or item['name'] in names:
                raise ValueError('ARCHIVE_PATH_DENIED')
            names.add(item['name'])
            log = confined(self.root, directory / item['name'])
            if log.stat().st_size > MAX_LOGS + MAX_JSON or (verify_content and file_hash(log) != item['compressed_sha256']):
                raise ValueError('ARCHIVE_CONTENT_CHANGED')
        return {'path': str(directory), 'manifest_sha256': file_hash(directory / 'manifest.json'), 'evidence_sha256': evidence_sha,
                'operation_id': operation, 'retention': 'KEEP_UNTIL_EXPLICIT_EXPORT_AND_REVIEW', 'log_count': len(manifest['logs'])}

    def discard_partial(self, partial):
        # Only our incomplete compressed copies; original logs are never touched.
        partial = confined(self.root, partial)
        if (partial.parent.parent != self.path('state/studio-archives')
                or not re.fullmatch('[a-f0-9]{32}', partial.parent.name)
                or not re.fullmatch(r'\.partial-[a-f0-9]{32}', partial.name)):
            raise ValueError('PARTIAL_PATH_DENIED')
        files = list(partial.iterdir())
        for path in files:
            confined(self.root, path)
            if not path.is_file() or (path.name not in {'stdout.log.gz', 'stderr.log.gz', 'manifest.json'}
                    and not re.fullmatch(r'\.manifest\.json-[a-f0-9]{32}\.tmp', path.name)):
                raise ValueError('PARTIAL_CONTENT_REQUIRES_REVIEW')
        for path in files:
            path.unlink()
        partial.rmdir()

    def archive(self, operation, expected):
        core, _ = self.evidence(operation)
        if core['files']['intent'] is None and core['ledger'] is None and core['files'].get('rejection') is None:
            raise ValueError('KNOWN_OPERATION_REQUIRED_FOR_ARCHIVE')
        result = self.status(operation)
        if result['evidence_sha256'] != expected:
            raise ValueError('STALE_EVIDENCE_REFRESH_REQUIRED')
        if result['state'] not in TERMINAL or self.path(f'host-state/pending/{operation}.json').exists() or self.path(f'host-state/running/{operation}.json').exists():
            raise ValueError('ACTIVE_LOGS_CANNOT_BE_ARCHIVED')
        if result['archive'] is not None:
            return result['archive']
        archive_root = self.path('state/studio-archives')
        entries = list(archive_root.glob('*/*')) if archive_root.exists() else []
        # All archive mutations hold the same Studio and worker locks. Thus no
        # other archive writer is live here, including after a prior 45s kill.
        for entry in entries:
            if entry.name.startswith('.partial-'):
                self.discard_partial(entry)
        entries = list(archive_root.glob('*/*')) if archive_root.exists() else []
        if len(entries) >= MAX_ARCHIVES:
            raise ValueError('ARCHIVE_CAPACITY_REQUIRES_EXPORT_REVIEW')
        total = 0
        for entry in entries:
            confined(self.root, entry)
            for path in entry.iterdir():
                total += confined(self.root, path).stat().st_size
        logs = []
        for name in ('stdout.log', 'stderr.log'):
            path = self.path(f'state/operations/{operation}/{name}')
            if path.exists():
                logs.append((name, path, path.stat().st_size))
        size = sum(item[2] for item in logs)
        if size > MAX_LOGS or total + size + MAX_JSON > MAX_RETAINED_BYTES:
            raise ValueError('ARCHIVE_CAPACITY_REQUIRES_EXPORT_REVIEW')
        parent = self.path(f'state/studio-archives/{operation}')
        parent.mkdir(parents=True, exist_ok=True)
        partial = confined(self.root, parent / ('.partial-' + uuid.uuid4().hex))
        partial.mkdir()
        manifest = {'schema': 'OpenRemaster.DevLogArchive.v1', 'operation_id': operation, 'scope': self.scope,
                    'evidence_sha256': expected, 'created_epoch': time.time(), 'production_go': False, 'logs': []}
        try:
            for name, source, expected_size in logs:
                before = source.stat()
                h, count = hashlib.sha256(), 0
                target = partial / (name + '.gz')
                with source.open('rb') as stream, target.open('xb') as output:
                    with gzip.GzipFile(filename='', mode='wb', fileobj=output, mtime=0) as archive:
                        for block in iter(lambda: stream.read(65536), b''):
                            count += len(block)
                            if count > MAX_LOGS or count > expected_size:
                                raise ValueError('LOG_CHANGED_DURING_ARCHIVE')
                            h.update(block)
                            archive.write(block)
                    output.flush()
                    os.fsync(output.fileno())
                after = source.stat()
                if count != expected_size or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise ValueError('LOG_CHANGED_DURING_ARCHIVE')
                row = self.ledger(operation)
                worker = (row or {}).get('result', {}).get('worker', {}) if row and row['result'] else {}
                recorded = worker.get('stdout_sha256' if name == 'stdout.log' else 'stderr_sha256')
                if recorded is not None and h.hexdigest() != recorded:
                    raise ValueError('TERMINAL_LOG_HASH_CHANGED')
                manifest['logs'].append({'name': target.name, 'original_bytes': count, 'original_sha256': h.hexdigest(), 'compressed_sha256': file_hash(target)})
            atomic_new(self.root, partial / 'manifest.json', manifest)
            if self.evidence(operation)[1] != expected:
                raise ValueError('EVIDENCE_CHANGED_DURING_ARCHIVE')
            partial.rename(self.path(f'state/studio-archives/{operation}/{expected}'))
            return self.archive_receipt(operation, expected)
        except BaseException:
            if partial.exists():
                self.discard_partial(partial)
            raise

    def reject(self, request):
        operation = request['operation_id']
        core, _ = self.evidence(operation)
        health = self.host.health()
        if (core['ledger'] is not None or any(value is not None for key, value in core['files'].items() if key != 'rejection')
                or health.get('operation_id') == operation):
            raise ValueError('NOT_ADMITTED_PROOF_UNAVAILABLE')
        old = core['files'].get('rejection')
        if old is not None:
            if old['attempt_id'] != request['attempt_id']:
                raise ValueError('REJECTED_OPERATION_CANNOT_BE_REUSED')
        else:
            if len(list(self.path('state/studio-rejections').glob('*.json'))) >= 4096:
                raise ValueError('REJECTION_CAPACITY_REQUIRES_REVIEW')
            atomic_new(self.root, self.path(f'state/studio-rejections/{operation}.json'), {
                'schema': 'OpenRemaster.NotAdmitted.v1', 'operation_id': operation, 'scope': self.scope,
                'attempt_id': request['attempt_id'], 'reason': request['reason'], 'production_go': False,
            })
        return self.status(operation)

    def export_logs(self, operation, expected):
        receipt = self.archive(operation, expected)
        directory = Path(receipt['path'])
        manifest = read_optional(self.root, directory / 'manifest.json')
        target = confined(self.root, directory / 'diagnostics.zip')
        if not target.exists():
            # The ZIP is another retained copy and counts against the existing quota.
            retained = sum(confined(self.root, p).stat().st_size for p in self.path('state/studio-archives').glob('*/*/*') if p.is_file())
            estimate = sum((directory / item['name']).stat().st_size for item in manifest['logs']) + MAX_JSON
            if retained + estimate > MAX_RETAINED_BYTES:
                raise ValueError('EXPORT_CAPACITY_REQUIRES_REVIEW')
            temporary = confined(self.root, directory / ('.export-' + uuid.uuid4().hex + '.tmp'))
            try:
                with zipfile.ZipFile(temporary, 'x', compression=zipfile.ZIP_STORED) as bundle:
                    bundle.write(directory / 'manifest.json', 'manifest.json')
                    for item in manifest['logs']:
                        bundle.write(directory / item['name'], item['name'])
                if temporary.stat().st_size > MAX_LOGS + MAX_JSON:
                    raise ValueError('EXPORT_SIZE')
                os.rename(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
        # An existing export must still contain exactly the retained manifest
        # and compressed logs, including on a later retry after interruption.
        expected_members = {'manifest.json': (file_hash(directory / 'manifest.json'), (directory / 'manifest.json').stat().st_size)}
        expected_members.update({item['name']: (item['compressed_sha256'], (directory / item['name']).stat().st_size) for item in manifest['logs']})
        with zipfile.ZipFile(target) as bundle:
            if len(bundle.infolist()) != len(expected_members) or set(bundle.namelist()) != set(expected_members):
                raise ValueError('EXPORT_MEMBERS_CHANGED')
            for info in bundle.infolist():
                expected_sha, expected_size = expected_members[info.filename]
                if info.compress_type != zipfile.ZIP_STORED or info.file_size != expected_size or info.file_size > MAX_LOGS:
                    raise ValueError('EXPORT_MEMBER_SIZE')
                with bundle.open(info) as stream:
                    h = hashlib.sha256()
                    for block in iter(lambda: stream.read(65536), b''):
                        h.update(block)
                if h.hexdigest() != expected_sha:
                    raise ValueError('EXPORT_MEMBER_CHANGED')
        return {'schema': 'OpenRemaster.DevLogExport.v1', 'operation_id': operation, 'scope': self.scope,
                'evidence_sha256': expected, 'manifest_sha256': receipt['manifest_sha256'],
                'bytes': target.stat().st_size, 'sha256': file_hash(target), 'production_go': False}

    def log_page(self, request):
        operation, expected = request['operation_id'], request['expected_evidence_sha256']
        if self.evidence(operation)[1] != expected:
            raise ValueError('STALE_EVIDENCE_REFRESH_REQUIRED')
        source, name = request['source'], request['name']
        offset, limit = request['offset'], request['limit']
        verified, full_sha, manifest_sha = False, None, None
        if source == 'live':
            path = self.path(f'state/operations/{operation}/{name}')
            with path.open('rb') as stream:
                total = os.fstat(stream.fileno()).st_size
                if total > MAX_LOGS:
                    raise ValueError('LOG_SIZE')
                stream.seek(offset)
                data = stream.read(min(limit, max(0, total - offset)))
        else:
            receipt = self.archive_receipt(operation, expected)
            if receipt is None or receipt['manifest_sha256'] != request['manifest_sha256']:
                raise ValueError('ARCHIVE_MANIFEST_CHANGED')
            directory = Path(receipt['path'])
            manifest_sha = receipt['manifest_sha256']
            if source == 'bundle':
                path = confined(self.root, directory / 'diagnostics.zip')
                total = path.stat().st_size
                if total > MAX_LOGS + MAX_JSON:
                    raise ValueError('EXPORT_SIZE')
                full_sha = file_hash(path)
                with path.open('rb') as stream:
                    stream.seek(offset)
                    data = stream.read(limit)
                if file_hash(path) != full_sha:
                    raise ValueError('EXPORT_CHANGED')
            else:
                manifest = read_optional(self.root, directory / 'manifest.json')
                item = next((item for item in manifest['logs'] if item['name'] == name + '.gz'), None)
                if item is None:
                    raise ValueError('LOG_NOT_ARCHIVED')
                total, h, data = 0, hashlib.sha256(), bytearray()
                with gzip.open(confined(self.root, directory / item['name']), 'rb') as stream:
                    for block in iter(lambda: stream.read(65536), b''):
                        end = total + len(block)
                        if end > MAX_LOGS:
                            raise ValueError('ARCHIVE_EXPANSION_LIMIT')
                        if end > offset and total < offset + limit:
                            data.extend(block[max(0, offset-total):min(len(block), offset+limit-total)])
                        h.update(block)
                        total = end
                full_sha = h.hexdigest()
                if total != item['original_bytes'] or full_sha != item['original_sha256']:
                    raise ValueError('ARCHIVE_ORIGINAL_HASH_CHANGED')
            verified = True
        if offset > total or self.evidence(operation)[1] != expected:
            raise ValueError('LOG_PAGE_CHANGED')
        return {'schema': 'OpenRemaster.DevLogPage.v1', 'operation_id': operation, 'scope': self.scope,
                'evidence_sha256': expected, 'manifest_sha256': manifest_sha, 'source': source, 'name': name,
                'offset': offset, 'next_offset': offset + len(data), 'total_bytes': total,
                'bytes_base64': base64.b64encode(data).decode('ascii'), 'chunk_sha256': digest(data),
                'file_sha256': full_sha, 'verified': verified, 'eof': offset + len(data) == total, 'production_go': False}


    @contextlib.contextmanager
    def mutation(self):
        # Reuse the same queue-submission and broker-writer locks, in that order.
        with self.host.lock('submit.lock') as queue_owned:
            if not queue_owned:
                raise ValueError('QUEUE_WRITER_BUSY')
            with self.api.writer() as worker_owned:
                if not worker_owned:
                    raise ValueError('BUILD_WRITER_BUSY')
                yield

    def execute(self, request):
        request = validate_request(request)
        if request['action'] in ('capabilities', 'status', 'logs'):
            return self._execute(request)
        # Serialize Studio's intent/resolution decisions as well as queue publication.
        with self.host.lock('studio-control.lock') as owned:
            if not owned:
                raise ValueError('STUDIO_CONTROL_BUSY')
            try:
                return self._execute(request)
            except ValueError as error:
                if request['action'] == 'submit' and 'attempt_id' in request:
                    with self.mutation():
                        core, _ = self.evidence(request['operation_id'])
                        if core['ledger'] is None and all(value is None for value in core['files'].values()):
                            return self.reject(dict(request, reason=str(error)[:2048]))
                raise

    def _execute(self, request):
        request = validate_request(request)
        operation, action = request['operation_id'], request['action']
        if action == 'capabilities':
            health = self.host.health()
            return {'healthy': health.get('healthy') is True, 'state': health.get('state', 'UNKNOWN'), 'production_go': False}
        if action == 'submit':
            if self.path(f'state/studio-rejections/{operation}.json').exists():
                raise ValueError('REJECTED_OPERATION_CANNOT_BE_RESUBMITTED')
            if self.path(f'state/studio-resolutions/{operation}.json').exists():
                raise ValueError('RESOLVED_OPERATION_CANNOT_BE_RESUBMITTED')
            intents = list(self.path('state/studio-intents').glob('*.json'))
            if len(intents) >= 4096:
                raise ValueError('INTENT_CAPACITY_REQUIRES_REVIEW')
            for path in intents:
                previous = read_optional(self.root, path)
                old = previous.get('operation_id', '')
                if not re.fullmatch('[a-f0-9]{32}', old) or path.stem != old or previous.get('scenario') != SCENARIO:
                    raise ValueError('PREVIOUS_INTENT_INVALID')
                if old == operation:
                    continue
                # Admission needs terminal disposition, not a fresh validation
                # of every historical artifact/toolchain. Status still performs
                # the full verification when that operation is inspected.
                core, sha = self.evidence(old)
                row = core['ledger']
                committed = (row is not None and row['state'] == 'COMMITTED'
                             and isinstance(row['result'], dict) and row['result'].get('state') == 'COMMITTED'
                             and row['result'].get('production_go') is False
                             and row['result'].get('worker', {}).get('owned_tree_stopped') is True
                             and row['launch_count'] == 1 and core['files']['done'] == row['result']
                             and core['files']['pending'] is None and core['files']['running'] is None)
                if not committed and self.resolution(old, sha, verify_content=False) is None:
                    raise ValueError('PREVIOUS_STUDIO_OPERATION_UNRESOLVED:' + old)
            for folder in ('pending', 'running'):
                for path in self.path('host-state/' + folder).glob('*.json'):
                    queued = read_optional(self.root, path)
                    if queued.get('scenario') == SCENARIO and queued.get('operation_id') != operation:
                        raise ValueError('STUDIO_WORK_ALREADY_QUEUED')
            intent = self.path(f'state/studio-intents/{operation}.json')
            if not intent.exists():
                value = {'operation_id': operation, 'scenario': SCENARIO, 'scope': self.scope, 'production_go': False}
                if 'dev_receipt_sha256' in request:
                    value['dev_receipt_sha256'] = request['dev_receipt_sha256']
                atomic_new(self.root, intent, value)
            # Existing host owns admission, durable ACK, the queue and execution.
            self.host.submit(operation, SCENARIO)
            return self.status(operation)
        if action == 'status':
            return self.status(operation)
        if action == 'logs':
            return self.log_page(request)
        with self.mutation():
            if action == 'reject':
                return self.reject(request)
            if action == 'export':
                return self.export_logs(operation, request['expected_evidence_sha256'])
            if action == 'archive':
                self.archive(operation, request['expected_evidence_sha256'])
            else:
                result = self.status(operation)
                if result['evidence_sha256'] != request['expected_evidence_sha256']:
                    raise ValueError('STALE_EVIDENCE_REFRESH_REQUIRED')
                if result['resolution'] is None:
                    if not result['recovery']['allowed']:
                        raise ValueError('RECOVERY_NOT_PROVEN_SAFE')
                    archive = self.archive(operation, result['evidence_sha256'])
                    receipt = {'schema': 'OpenRemaster.DevHoldResolution.v1', 'operation_id': operation, 'scope': self.scope,
                               'evidence_sha256': result['evidence_sha256'], 'archive_manifest_sha256': archive['manifest_sha256'],
                               'reason': request['reason'].strip(), 'disposition': 'ACKNOWLEDGED_NO_RETRY', 'created_epoch': time.time(), 'production_go': False}
                    atomic_new(self.root, self.path(f'state/studio-resolutions/{operation}.json'), receipt)
            return self.status(operation)


def load_control(config, scope):
    root = Path(config['root'])
    if not root.is_absolute() or root.resolve() != root:
        raise ValueError('CANONICAL_WORKER_ROOT_REQUIRED')
    confined(root, root)
    for name, key in [('broker.py', 'broker_sha256'), ('host.py', 'host_sha256'), ('BROKER-PINS.json', 'manifest_sha256'), ('WORKER-CONFIG.json', 'worker_config_sha256')]:
        if file_hash(confined(root, root / name)) != config[key]:
            raise ValueError('CONTROL_PIN_CHANGED:' + name)
    worker = read_optional(root, root / 'WORKER-CONFIG.json')
    if worker.get('profile') != 'DEV_UNSIGNED' or worker.get('production_go') is not False or Path(worker.get('root', '')).resolve() != root:
        raise ValueError('DEV_WORKER_PROFILE_REQUIRED')
    if Path(sys.executable).resolve() != Path(config['python']).resolve() or file_hash(Path(sys.executable)) != config['python_sha256']:
        raise ValueError('CONTROL_PYTHON_PIN_CHANGED')
    def load(name):
        spec = importlib.util.spec_from_file_location('studio_pinned_' + name, root / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    api = load('broker')
    api.verify_runtime()
    host = load('host')
    return Control(root, api, host, scope)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--request', required=True)
    args = parser.parse_args()
    config = decode(args.config)
    request = validate_request(decode(args.request))
    scope = digest(json.dumps(config, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())
    control = load_control(config, scope)
    result = control.execute(request)
    print(json.dumps(result, separators=(',', ':')))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'error': type(error).__name__ + ':' + str(error), 'production_go': False, 'automatic_retry': False}))
        sys.exit(75)
