"""Capture a read-only README gate result for an archived acceptance report."""

import argparse
from datetime import datetime, timezone
from hashlib import file_digest, sha256
import importlib.util
import json
from pathlib import Path
import re
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', type=Path, required=True)
    parser.add_argument('--project', required=True)
    parser.add_argument('--build-id', required=True)
    parser.add_argument('--validator', type=Path, required=True)
    parser.add_argument('--package-manifest', action='store_true',
                        help='Use SHA256SUMS.txt in a package named for the build')
    args = parser.parse_args()

    if args.package_manifest:
        if args.build_dir.name != args.build_id:
            parser.error('Build ID does not match package directory')
        evidence = (args.build_dir / 'SHA256SUMS.txt').read_bytes()
        entries = {}
        for line in evidence.decode('ascii').splitlines():
            match = re.fullmatch(r'([a-fA-F0-9]{64})  ([A-Za-z0-9_.-]+)', line)
            if not match or match[2] in ('.', '..') or match[2] in entries:
                parser.error('Malformed package checksum entry')
            entries[match[2]] = match[1].lower()
        if not entries:
            parser.error('Empty package checksum manifest')
        for name, expected in entries.items():
            with (args.build_dir / name).open('rb') as artifact:
                if file_digest(artifact, 'sha256').hexdigest() != expected:
                    parser.error(f'Package checksum mismatch for {name}')
        binding = {'packageManifestSha256': sha256(evidence).hexdigest()}
    else:
        acceptance = (args.build_dir / 'ACCEPTANCE.json').read_bytes()
        if json.loads(acceptance).get('candidate') != args.build_id:
            parser.error('Build ID does not match ACCEPTANCE.json')
        binding = {'acceptanceSha256': sha256(acceptance).hexdigest()}

    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('dev_build_readme_validator', args.validator)
    if spec is None or spec.loader is None:
        parser.error('README validator must be a Python module')
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)

    try:
        problems = validator.scan(args.build_dir, args.project, args.build_id)
    except (OSError, UnicodeError):
        status = 'UNKNOWN'
        problems = ['README.md could not be read.']
    else:
        status = 'README_HOLD' if problems else 'README_GATE_PASS'
        # Keep this snapshot portable and omit the build directory from diagnostics.
        path = str(args.build_dir / 'README.md')
        problems = [problem.replace(path, 'README.md') for problem in problems]

    print(json.dumps({
        'schema': 'OpenRemaster.StudioReadmeCheck.v1',
        'projectId': args.project,
        'buildId': args.build_id,
        **binding,
        'checkedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'validator': args.validator.name,
        'validatorSha256': sha256(args.validator.read_bytes()).hexdigest(),
        'status': status,
        'problems': problems,
    }, indent=2))


if __name__ == '__main__':
    main()
