"""Bind README controls review to this exact source snapshot; no release authority."""
import argparse
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess


def source_files(studio):
    files = set()
    for folder in ('src', 'src-tauri/src', 'src-tauri/capabilities'):
        files.update(path for path in (studio / folder).rglob('*') if path.is_file())
    files.update(studio / path for path in (
        'index.html', 'package.json', 'package-lock.json', 'WINDOWS-DEV.txt',
        'vite.config.ts', 'tsconfig.json', 'src-tauri/build.rs', 'src-tauri/dev-worker-pins.json', 'src-tauri/local-status-pins.json', 'src-tauri/local-status-v2-pins.json', 'tools/studio_dev_control.py',
        'src-tauri/Cargo.toml', 'src-tauri/Cargo.lock', 'src-tauri/tauri.conf.json',
        'tools/package-windows-dev.ps1', 'tools/verify_dev_build_readme.py', 'tools/verify_controls_review.py'))
    result = {}
    for path in sorted(files):
        for part in (path, *path.parents):
            if part.is_symlink() or getattr(part.lstat(), 'st_file_attributes', 0) & 0x400:
                raise ValueError('Review source contains a reparse path')
            if part == studio:
                break
        if not path.resolve().is_relative_to(studio):
            raise ValueError('Review source escapes Studio')
        raw = path.read_bytes()
        if path.suffix.lower() != '.png':
            raw = raw.replace(b'\r\n', b'\n')
        result[path.relative_to(studio).as_posix()] = sha256(raw).hexdigest()
    return result


def fingerprint(files):
    return sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def verify(studio, commit):
    if not re.fullmatch('[a-f0-9]{40}', commit):
        raise ValueError('Exact Git commit required')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=studio, text=True).strip()
    if head != commit:
        raise ValueError('Package commit differs from checked-out source')
    path = studio / 'tools/controls-review.json'
    raw = path.read_bytes()
    record = json.loads(raw)
    if (record.get('schema') != 'OpenRemaster.StudioControlsReview.v1' or record.get('production_go') is not False
            or record.get('decision') != 'SOURCE_CONTROLS_VERIFIED' or record.get('scope') != 'SOURCE_CONTROLS_ONLY'
            or record.get('hash_method') != 'SHA256_TEXT_LF_BINARY_RAW'
            or not isinstance(record.get('reviewer'), str) or not 1 <= len(record['reviewer']) <= 128
            or date.fromisoformat(record['reviewed_at']) > datetime.now(timezone.utc).date()):
        raise ValueError('Controls review identity or scope rejected')
    files = source_files(studio)
    subprocess.check_output(['git', 'ls-files', '--error-unmatch', '--', *files, 'tools/controls-review.json'], cwd=studio, stderr=subprocess.STDOUT)
    if subprocess.run(['git', 'diff', '--no-ext-diff', '--ignore-cr-at-eol', '--quiet', commit, '--', *files, 'tools/controls-review.json'], cwd=studio).returncode:
        raise ValueError('Studio contains changes outside the declared commit')
    if record.get('files') != files or record.get('source_fingerprint') != fingerprint(files):
        raise ValueError('Source changed since controls review; obtain a new source review')
    return {'source_commit': commit, 'reviewer': record['reviewer'], 'reviewed_at': record['reviewed_at'],
            'source_fingerprint': record['source_fingerprint'], 'record_sha256': sha256(raw).hexdigest(),
            'scope': 'SOURCE_CONTROLS_ONLY', 'hash_method': 'SHA256_TEXT_LF_BINARY_RAW', 'production_go': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--studio', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.studio.resolve(), args.commit)))
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        raise SystemExit('README_HOLD: ' + str(error))
