"""Validate committed licensing material and its byte-for-byte archive copies."""

import argparse
import hashlib
import json
import tarfile
import zipfile
from pathlib import Path

if __package__:
    from .publication_policy import publication_packages
    from .license_pointers import resolve_pointer, verified_recoveries
else:
    from publication_policy import publication_packages
    from license_pointers import resolve_pointer, verified_recoveries


REQUIRED = ('THIRD_PARTY_NOTICES.md', 'LICENSING.md', 'third_party/inventory.json',
            'third_party/fonts.json', 'third_party/supplemental.json')


def license_files(root, require_publishable=False, platform=None):
    if platform and not require_publishable:
        raise ValueError('platform requires require_publishable=True')
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
    active = publication_packages(root, platform, inventory) if require_publishable and platform else None
    for package in inventory['packages']:
        in_scope = active is None or f"{package['name']} {package['version']}" in active
        contents = {n['path']: (root / n['path']).read_bytes() for n in package['notices']}
        recoveries = verified_recoveries(package, supplements, contents)
        for notice in package['notices']:
            resolution = resolve_pointer(notice['path'], contents, recoveries)
            if notice.get('pointer') != resolution:
                raise ValueError(f"Pointer resolution mismatch: {notice['path']}")
            if resolution and resolution['status'] != 'resolved' and require_publishable and in_scope:
                raise ValueError(f"Unresolved license pointer: {notice['path']}")
    if require_publishable:
        issues = [(p['name'], p['issues']) for p in inventory['packages'] if p['issues'] and (active is None or f"{p['name']} {p['version']}" in active)]
        if issues:
            raise ValueError(f'Unresolved third-party inventory issues: {issues}')
    return sorted(paths)


def verify_archive(root, archive, require_publishable=False, platform=None):
    if platform:
        extension = 'tar.gz' if platform == 'linux-x64' else 'zip'
        if archive.name != f'pdf-squeeze-{platform}.{extension}':
            raise ValueError(f'Archive does not match publication platform: {archive.name}')
    paths = license_files(root, require_publishable, platform)
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
    parser.add_argument('--require-publishable', action='store_true', help='Require project LICENSE and no in-scope inventory issues; does not grant legal clearance')
    parser.add_argument('--platform', help='Use the reviewed Windows/Linux publication scope')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    paths = license_files(root, args.require_publishable, args.platform)
    for archive in args.archive:
        verify_archive(root, archive, args.require_publishable, args.platform)
    print(f'Verified {len(paths)} licensing files and {len(args.archive)} archives')


if __name__ == '__main__':
    main()
