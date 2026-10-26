"""Enforce a reviewed, default-feature platform scope without clearing inventory gaps."""
import hashlib
import json
import re
import subprocess
import sys


TARGETS = {
    'windows-x64': 'x86_64-pc-windows-msvc',
    'linux-x64': 'x86_64-unknown-linux-gnu',
}
REVIEW_INPUTS = {'Cargo.lock', 'Cargo.toml', 'src/gs.rs', 'build.rs',
                'third_party/inventory.json', 'third_party/fonts.json',
                'third_party/supplemental.json'}


def publication_packages(root, platform, inventory):
    if platform not in TARGETS:
        raise ValueError(f'Platform not approved for publication: {platform}')
    policy = json.loads((root / 'third_party/publication-policy.json').read_text(encoding='utf-8'))
    if policy['schema'] != 1 or not REVIEW_INPUTS.issubset(policy['inputs']):
        raise ValueError('Invalid publication policy or missing review inputs')
    for path, expected in policy['inputs'].items():
        source = root / path
        if source.is_symlink() or not source.resolve().is_relative_to(root.resolve()):
            raise ValueError(f'Unsafe publication review input: {path}')
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Publication review input changed: {path}')
    scope = policy['platforms'][platform]
    if scope['target'] != TARGETS[platform]:
        raise ValueError(f'Publication target mismatch: {platform}')
    output = subprocess.check_output([
        'cargo', 'tree', '--locked', '--offline', '--color', 'never',
        '--target', TARGETS[platform], '--edges', 'normal,build',
        '--prefix', 'none', '--format', '{p}',
    ], cwd=root, text=True)
    active = set()
    roots = 0
    for line in output.splitlines():
        match = re.fullmatch(r'([A-Za-z0-9_-]+) v([^\s]+)(?: \([^\n]*\))*', line)
        if not match:
            raise ValueError(f'Unexpected Cargo tree entry: {line}')
        name, version = match.groups()
        if name == 'pdf-squeeze':
            roots += 1
        else:
            active.add(f'{name} {version}')
    expected_tree = scope['inspection_trees'].get(sys.platform)
    if roots != 1 or not active or expected_tree is None or active != set(expected_tree):
        raise ValueError(f'Publication dependency tree changed: {platform} on {sys.platform}')
    # A Linux inspection omits Windows-host build dependencies. They remain in
    # the reviewed native obligations scope, verified again on the native runner.
    if not active.issubset(scope['packages']):
        raise ValueError(f'Publication tree escapes native scope: {platform}')
    active = set(scope['packages'])
    packages = {f"{p['name']} {p['version']}": p for p in inventory['packages']}
    for key in active:
        package = packages.get(key)
        if not package or not package['notices'] or package['license'] not in policy['license_choices']:
            raise ValueError(f'Unreviewed grant or missing terms: {key}')
        if package['issues']:
            raise ValueError(f"Unresolved active inventory issues: {key}: {package['issues']}")
    return active
