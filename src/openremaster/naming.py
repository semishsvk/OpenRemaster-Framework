# Generated source integration from existing harmonization.py SHA256 6af7052e8ab7548e0766855395ccbd7e265d5849e06078bb615a3d0e6382487e; keep the contract source-bound.
"""Alias-first naming contracts. Never mutates source projects or resolves ambiguity."""
import argparse
import json
import re
from pathlib import Path

STATES = {'VERIFIED_COMPLETE', 'VERIFIED_PARTIAL', 'PLANNED', 'UNKNOWN', 'CONFLICT', 'STALE'}
MIGRATIONS = {'SAFE_WITH_ALIAS', 'REQUIRES_REGRESSION', 'BLOCKED_BY_DEPENDENCY', 'BLOCKED_BY_PROVENANCE', 'UNKNOWN'}
ID_PATTERN = r'[a-z][a-z0-9]*(?:\.[a-z][a-z0-9]*)+'
REQUIRED = {'component_id', 'project_id', 'edition_id', 'artifact_id', 'canonical_name',
            'display_name', 'legacy_aliases', 'owner', 'source_path', 'manifest_path',
            'version', 'provenance', 'dependencies', 'verification_state', 'migration_state'}

class ResolutionError(ValueError):
    pass

def validate(records):
    if not isinstance(records, list) or len(records) > 10000:
        raise ValueError('Invalid component collection')
    ids = set()
    for r in records:
        if not isinstance(r, dict) or not REQUIRED <= r.keys():
            raise ValueError('Missing required fields')
        if set(r) - REQUIRED - {'component_type'}:
            raise ValueError('Unknown component configuration key')
        ident = r['component_id']
        if not isinstance(ident, str) or not re.fullmatch(ID_PATTERN, ident) or ident in ids:
            raise ValueError('Invalid or duplicate component identity')
        ids.add(ident)
        if not isinstance(r['verification_state'],str) or r['verification_state'] not in STATES:
            raise ValueError('Invalid verification state')
        if not isinstance(r['migration_state'],str) or r['migration_state'] not in MIGRATIONS:
            raise ValueError('Invalid migration state')
        for key in ('project_id', 'canonical_name', 'display_name'):
            if not isinstance(r[key],str) or not r[key].strip() or len(r[key]) > 512:
                raise ValueError('Invalid string field: '+key)
        for key in ('edition_id','artifact_id','owner','source_path','manifest_path','version'):
            if r[key] is not None and (not isinstance(r[key],str) or not r[key].strip()):
                raise ValueError('Invalid nullable string field: '+key)
        if 'component_type' in r and (not isinstance(r['component_type'],str) or not r['component_type'].strip() or len(r['component_type'])>512):
            raise ValueError('Invalid component type')
        if not isinstance(r['legacy_aliases'], list) or not isinstance(r['dependencies'], list):
            raise ValueError('Aliases and dependencies must be lists')
        for key in ('legacy_aliases','dependencies'):
            if any(not isinstance(x,str) or not x.strip() for x in r[key]) or len(set(r[key])) != len(r[key]):
                raise ValueError('Invalid or duplicate '+key)
        if not isinstance(r['provenance'],list):raise ValueError('Invalid provenance collection')
        for entry in r['provenance']:
            if not isinstance(entry,dict) or set(entry)!={'path','sha256','role'}:
                raise ValueError('Invalid provenance entry')
            if any(not isinstance(entry[k],str) or not entry[k].strip() for k in entry):
                raise ValueError('Invalid provenance entry values')
            if not re.fullmatch(r'[a-f0-9]{64}',entry['sha256']):raise ValueError('Invalid provenance SHA256')
    for r in records:
        if any(dep not in ids or dep == r['component_id'] for dep in r['dependencies']):
            raise ValueError('Dangling or self dependency')
    return True

def read_registry(path):
    def pairs(items):
        out={}
        for key,value in items:
            if key in out:raise ValueError('Duplicate JSON key: '+key)
            out[key]=value
        return out
    def constant(value):raise ValueError('Nonfinite JSON number: '+value)
    with Path(path).open('rb') as stream:raw=stream.read(4_000_001)
    if len(raw)>4_000_000:raise ValueError('Registry exceeds byte bound')
    data=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=pairs,parse_constant=constant)
    if not isinstance(data,dict) or set(data)!={'schema','status','owner_admission','components','logical_identity_basis'}:
        raise ValueError('Invalid registry envelope')
    if data['schema']!='orf.naming.components.v3' or data['status']!='SOURCE_ONLY_CANDIDATE' or data['owner_admission'] is not False:
        raise ValueError('Unsupported registry schema or authority claim')
    if not isinstance(data['logical_identity_basis'],str) or not data['logical_identity_basis'].strip():raise ValueError('Invalid identity basis')
    validate(data['components'])
    return data

def resolve(records, alias, project_id=None, edition_id=None):
    validate(records)
    matches = [r for r in records if alias in [r['component_id'], r['canonical_name'], *r['legacy_aliases']]
               and (project_id is None or r['project_id'] == project_id)
               and (edition_id is None or r['edition_id'] == edition_id)]
    if len(matches) != 1:
        raise ResolutionError('UNKNOWN_ALIAS' if not matches else 'AMBIGUOUS_ALIAS_REQUIRE_PROJECT_AND_EDITION')
    result = matches[0]
    if result['verification_state'] not in {'VERIFIED_COMPLETE', 'VERIFIED_PARTIAL'}:
        raise ResolutionError('UNVERIFIED_IDENTITY')
    return result

def duplicates(records):
    groups = {}
    for r in records:
        name = re.sub(r'[^a-z0-9]', '', r['canonical_name'].casefold())
        groups.setdefault(name, []).append(r['component_id'])
    return {k: v for k, v in groups.items() if len(v) > 1}

def resource_status(reference, project_root):
    if not reference.startswith('res://'):
        return 'UNKNOWN_RESOURCE_SCHEME'
    root=Path(project_root).resolve()
    target=(root/reference[6:]).resolve()
    if not target.is_relative_to(root):
        return 'OUTSIDE_PROJECT'
    try:
        return 'PRESENT' if target.is_file() else 'MISSING'
    except OSError:
        return 'ACCESS_DENIED'

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('registry', type=Path)
    p.add_argument('--resolve')
    p.add_argument('--project')
    p.add_argument('--edition')
    a = p.parse_args()
    try:
        for value in (a.resolve, a.project, a.edition):
            if value is not None and not value.strip():
                raise ResolutionError('EMPTY_SELECTION_OR_SCOPE')
        if (a.project is not None or a.edition is not None) and a.resolve is None:
            raise ResolutionError('PROJECT_EDITION_SCOPE_REQUIRES_RESOLVE')
        records = read_registry(a.registry)['components']
        result = resolve(records, a.resolve, a.project, a.edition) if a.resolve else {'valid': True, 'components': len(records), 'duplicate_names': duplicates(records)}
        print(json.dumps(result, indent=2))
    except (OSError,UnicodeError,ValueError) as exc:
        print(json.dumps({'status': 'HOLD', 'reason': str(exc)}))
        return 75
    return 0

if __name__ == '__main__':
    raise SystemExit(main())


def resolve_manifest_component(manifest, registry_path):
    """Resolve an explicitly scoped component reference; preserve legacy project identity.

    Optional metadata keys: orf_component_ref, orf_project_id, orf_edition_id.
    This is a source-only identity reference, never owner or execution admission.
    """
    from collections.abc import Mapping
    from .manifest import ProjectManifest
    if not isinstance(manifest, ProjectManifest):
        raise ValueError("ProjectManifest instance required")
    manifest.validate()
    metadata = manifest.metadata
    if not isinstance(metadata, Mapping) or "orf_component_ref" not in metadata:
        return None
    for key in ("orf_component_ref", "orf_project_id"):
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            raise ValueError("Explicit nonempty naming metadata required: " + key)
    edition = metadata.get("orf_edition_id")
    if edition is not None and (not isinstance(edition, str) or not edition.strip()):
        raise ValueError("Explicit edition must be a nonempty string")
    records = read_registry(registry_path)["components"]
    component = resolve(records, metadata["orf_component_ref"], metadata["orf_project_id"], edition)
    if component["edition_id"] is not None and edition is None:
        raise ValueError("Explicit edition required for edition-specific component")
    return {
        "schema": "orf.naming.manifest_reference.v1",
        "manifest_project_id": manifest.project_id,
        "component_id": component["component_id"],
        "registry_project_id": component["project_id"],
        "edition_id": component["edition_id"],
        "display_name": component["display_name"],
        "identity_verification_state": component["verification_state"],
        "migration_state": component["migration_state"],
        "semantic_completion": "UNKNOWN",
        "owner_admission": False,
        "rename_authorized": False,
        "execution_authorized": False,
    }
