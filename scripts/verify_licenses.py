"""Validate committed licensing material and its byte-for-byte archive copies."""

import argparse
import hashlib
import json
import tarfile
import zipfile
from pathlib import Path


REQUIRED = ('THIRD_PARTY_NOTICES.md', 'LICENSING.md', 'third_party/inventory.json',
            'third_party/fonts.json', 'third_party/supplemental.json')


def license_files(root, require_publishable=False):
    paths = set(REQUIRED)
    paths.update(p.relative_to(root).as_posix() for p in (root / 'third_party').rglob('*') if p.is_file())
    if require_publishable or (root / 'LICENSE').exists():
        paths.add('LICENSE')
    for path in paths:
        source = root / path
        if source.is_symlink() or not source.resolve().is_relative_to(root.resolve()):
            raise ValueError(f'License path escapes repository: {path}')
        if not source.read_bytes().strip():
            raise ValueError(f'Empty license documentation: {path}')
    inventory = json.loads((root / 'third_party/inventory.json').read_text(encoding='utf-8'))
    fonts = json.loads((root / 'third_party/fonts.json').read_text(encoding='utf-8'))
    supplements = json.loads((root / 'third_party/supplemental.json').read_text(encoding='utf-8'))
    if inventory['schema'] != 1 or not inventory['packages'] or not isinstance(fonts, list) or not isinstance(supplements, list):
        raise ValueError('Invalid license inventory schema')
    if hashlib.sha256((root / 'Cargo.lock').read_bytes()).hexdigest() != inventory['cargo_lock_sha256']:
        raise ValueError('License inventory is stale: Cargo.lock changed')
    for entry in supplements + [n for p in inventory['packages'] for n in p['notices']]:
        if entry['path'] not in paths or not entry['path'].startswith('third_party/'):
            raise ValueError(f"Missing or unsafe notice path: {entry['path']}")
        if hashlib.sha256((root / entry['path']).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(f"Notice checksum mismatch: {entry['path']}")
    if require_publishable:
        issues = [(p['name'], p['issues']) for p in inventory['packages'] if p['issues']]
        if issues:
            raise ValueError(f'Unresolved third-party inventory issues: {issues}')
    return sorted(paths)


def verify_archive(root, archive, require_publishable=False):
    paths = license_files(root, require_publishable)
    if archive.name.endswith('.zip'):
        with zipfile.ZipFile(archive) as package:
            for path in paths:
                if package.read(path) != (root / path).read_bytes():
                    raise ValueError(f'Archive license differs: {path}')
    else:
        with tarfile.open(archive, 'r:gz') as package:
            for path in paths:
                member = package.getmember(path)
                if not member.isfile() or package.extractfile(member).read() != (root / path).read_bytes():
                    raise ValueError(f'Archive license differs: {path}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, action='append', default=[])
    parser.add_argument('--require-publishable', action='store_true', help='Require project LICENSE and no inventory issues; does not grant legal clearance')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    paths = license_files(root, args.require_publishable)
    for archive in args.archive:
        verify_archive(root, archive, args.require_publishable)
    print(f'Verified {len(paths)} licensing files and {len(args.archive)} archives')


if __name__ == '__main__':
    main()
