"""Preserve locked crate notices; no license expression rewriting or legal clearance.

Run cargo fetch --locked first. Generation and --check use only local sources.
"""

import argparse
import hashlib
import json
import re
import struct
import subprocess
from collections import defaultdict
from pathlib import Path


TARGETS = {
    'windows-x64': 'x86_64-pc-windows-msvc',
    'linux-x64': 'x86_64-unknown-linux-gnu',
    'macos-arm64': 'aarch64-apple-darwin',
    'macos-x64': 'x86_64-apple-darwin',
}
NOTICE_NAME = re.compile(r'^(licen[cs]e|notice|copying|copyright|authors|ofl|ufl|unlicense)([-._]|$)', re.I)
SOURCE_SUFFIXES = {'.rs', '.c', '.cc', '.cpp', '.cxx', '.h', '.hpp', '.py', '.js', '.ts'}
RESOURCE_SUFFIXES = {'.ttf', '.otf', '.png', '.jpg', '.jpeg', '.ico', '.icns', '.svg', '.spv', '.metallib'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8')


def dependency_roles(metadata):
    """Conservative graph paths: normal vs build (including proc-macro closures).

    Cargo's platform-filtered metadata is not a linker map; host/target feature
    unification can over-include packages. Dev-only edges are excluded here.
    """
    nodes = {node['id']: node for node in metadata['resolve']['nodes']}
    macros = {p['id'] for p in metadata['packages']
              if any('proc-macro' in t['kind'] for t in p['targets'])}
    roles = defaultdict(set)
    pending = [(metadata['resolve']['root'], 'normal')]
    while pending:
        package, role = pending.pop()
        if role in roles[package]:
            continue
        roles[package].add(role)
        for dep in nodes.get(package, {}).get('deps', []):
            for edge in dep['dep_kinds']:
                if edge['kind'] == 'dev':
                    continue
                child_role = 'build' if role == 'build' or edge['kind'] == 'build' or dep['pkg'] in macros else 'normal'
                pending.append((dep['pkg'], child_role))
    return {key: sorted(value) for key, value in roles.items()}


def font_names(data):
    """Extract original SFNT name records; retain raw bytes as well as text."""
    tables = struct.unpack_from('>H', data, 4)[0]
    for index in range(tables):
        tag, _, offset, _ = struct.unpack_from('>4sIII', data, 12 + index * 16)
        if tag != b'name':
            continue
        _, count, storage = struct.unpack_from('>HHH', data, offset)
        records = []
        for record in range(count):
            platform, encoding, language, name, length, start = struct.unpack_from(
                '>HHHHHH', data, offset + 6 + record * 12)
            if name not in (0, 7, 8, 9, 11, 13, 14):
                continue
            raw = data[offset + storage + start:offset + storage + start + length]
            codec = 'utf-16-be' if platform in (0, 3) else 'mac_roman' if platform == 1 and encoding == 0 else None
            records.append(dict(platform=platform, encoding=encoding, language=language,
                                name_id=name, raw_hex=raw.hex(),
                                text=raw.decode(codec) if codec else None))
        return records
    return []


def collect(repo_root, metadata, target_metadata):
    files = {}
    packages = []
    fonts = []
    roles = {target: dependency_roles(value) for target, value in target_metadata.items()}
    supplements = json.loads((repo_root / 'third_party/supplemental.json').read_text(encoding='utf-8'))
    for entry in supplements:
        path = repo_root / entry['path']
        if not path.resolve().is_relative_to((repo_root / 'third_party/upstream').resolve()):
            raise ValueError(f"Supplement outside upstream directory: {entry['path']}")
        if digest(path.read_bytes()) != entry['sha256']:
            raise ValueError(f"Supplement checksum mismatch: {entry['path']}")
    labels = {p['id']: f"{p['name']} {p['version']} ({p['source'] or 'workspace'})" for p in metadata['packages']}
    incoming = defaultdict(list)
    for node in metadata['resolve']['nodes']:
        for dep in node['deps']:
            for edge in dep['dep_kinds']:
                incoming[dep['pkg']].append(dict(package=labels.get(node['id'], node['id']), kind=edge['kind'] or 'normal', target=edge['target']))
    for package in sorted(metadata['packages'], key=lambda p: (p['name'], p['version'])):
        if package['source'] is None:
            continue  # Project license is deliberately separate.
        key = package['name'] + '-' + package['version']
        source = Path(package['manifest_path']).parent
        notices = []
        resources = []
        issues = []
        for path in sorted(source.rglob('*'), key=lambda p: p.relative_to(source).as_posix()):
            if not path.is_file():
                continue
            relative = path.relative_to(source).as_posix()
            is_notice = (NOTICE_NAME.match(path.name) and path.suffix.lower() not in SOURCE_SUFFIXES) or (
                'fonts' in path.relative_to(source).parts and path.suffix.lower() == '.txt')
            if package['license_file'] and path == source / package['license_file']:
                is_notice = True
            if is_notice:
                data = path.read_bytes()
                if not data.strip():
                    issues.append(f'Empty upstream notice: {relative}')
                    continue
                destination = f'third_party/licenses/{key}/{relative}'
                files[destination] = data
                notices.append(dict(path=destination, source=f'{key}/{relative}', sha256=digest(data)))
            if path.suffix.lower() in RESOURCE_SUFFIXES:
                data = path.read_bytes()
                resources.append(dict(path=relative, sha256=digest(data)))
                if path.suffix.lower() == '.ttf':
                    fonts.append(dict(package=key, path=relative, sha256=digest(data), names=font_names(data)))
        for entry in supplements:
            if key in entry['crates']:
                notices.append(dict(path=entry['path'], source=entry['url'], sha256=entry['sha256']))
                issues.extend(entry.get('issues', []))
        if not notices:
            issues.append('No license or notice text found')
        if not package['license']:
            issues.append('No declared license expression')
        vcs = source / '.cargo_vcs_info.json'
        packages.append(dict(name=package['name'], version=package['version'], source=package['source'],
                             repository=package['repository'], license=package['license'],
                             authors=package['authors'], upstream_vcs=json.loads(vcs.read_text()) if vcs.exists() else None,
                             targets={target: mapping.get(package['id'], []) for target, mapping in roles.items()},
                             incoming=sorted(incoming[package['id']], key=lambda e: (e['package'], e['kind'], e['target'] or '')),
                             notices=notices, resources=resources, issues=issues))
    inventory = dict(schema=1, cargo_lock_sha256=digest((repo_root / 'Cargo.lock').read_bytes()),
                     target_triples=TARGETS, packages=packages)
    files['third_party/inventory.json'] = json_bytes(inventory)
    files['third_party/fonts.json'] = json_bytes(fonts)
    lines = ['# Third-party notices', '',
             'This inventory preserves upstream declarations and notice texts. It is engineering',
             'evidence, not a legal determination or a grant of rights for pdf-squeeze.', '',
             f"Coverage: **{len(packages)} third-party locked Rust packages**, including optional,",
             'build and target-specific dependencies. All four archives carry the same conservative',
             'superset. Inclusion does not assert that a crate is linked into every executable.', '',
             'License expressions below are copied verbatim, including legacy slash syntax;',
             'no alternative license has been selected or expression reclassified.', '',
             '- [Inventory and dependency paths](third_party/inventory.json)',
             '- [Embedded font copyright and license records](third_party/fonts.json)',
             '- [Scope, reproduction and outstanding questions](LICENSING.md)',
             '- [Pinned supplemental source provenance](third_party/supplemental.json)', '',
             'The project LICENSE, application icon rights, and external Ghostscript licensing',
             'are separate review items described in LICENSING.md. Ghostscript is not bundled.', '',
             '## Embedded fonts', '',
             'epaint_default_fonts embeds Hack, Noto Emoji, Ubuntu Light and emoji-icon-font.',
             'The entries below link Hack’s MIT and Bitstream Vera texts, SIL OFL 1.1,',
             'Ubuntu Font Licence 1.0, and John Slegers’ MIT notice. Linux window decorations',
             'also contain Cantarell (SIL OFL 1.1); its records and license text are included.',
             'Font name-table records',
             '(including original copyright strings) are preserved in fonts.json.', '',
             '## Crates', '']
    for p in packages:
        lines.extend([f"### {p['name']} {p['version']}", '', f"Declared license: `{p['license'] or 'UNDECLARED'}`", ''])
        for notice in p['notices']:
            lines.append(f"- [{notice['path']}]({notice['path']})")
        for issue in p['issues']:
            lines.append(f'- **Unresolved:** {issue}')
        lines.append('')
    files['THIRD_PARTY_NOTICES.md'] = ('\n'.join(lines).rstrip() + '\n').encode('utf-8')
    return files


def write_or_check(root, files, check):
    managed = {p for p in ('THIRD_PARTY_NOTICES.md', 'third_party/inventory.json', 'third_party/fonts.json')
               if (root / p).is_file()}
    managed.update(p.relative_to(root).as_posix() for p in (root / 'third_party/licenses').rglob('*') if p.is_file())
    differences = [p for p, data in files.items() if not (root / p).is_file() or (root / p).read_bytes() != data]
    stale = managed - files.keys()
    if check:
        for path in sorted(set(differences) | stale):
            print(f'License material missing, stale or changed: {path}')
        return not differences and not stale
    for path in stale:
        (root / path).unlink(missing_ok=True)
    for path, data in files.items():
        destination = root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Compare without modifying files')
    parser.add_argument('--require-complete', action='store_true', help='Fail for unresolved inventory issues (publication gate)')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent

    def metadata(target=None):
        command = ['cargo', 'metadata', '--locked', '--offline', '--format-version', '1']
        if target:
            command.extend(['--filter-platform', target])
        return json.loads(subprocess.check_output(command, cwd=root))

    files = collect(root, metadata(), {key: metadata(value) for key, value in TARGETS.items()})
    valid = write_or_check(root, files, args.check)
    inventory = json.loads(files['third_party/inventory.json'])
    unresolved = [p for p in inventory['packages'] if p['issues']]
    print(f"{len(inventory['packages'])} crates; {len(unresolved)} with unresolved inventory issues")
    if not valid or (args.require_complete and unresolved):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
