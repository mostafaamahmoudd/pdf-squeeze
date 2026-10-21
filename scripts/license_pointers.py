"""Resolve notice pointers using packaged bytes only; never follow filesystem paths."""

import re
from pathlib import PurePosixPath, PureWindowsPath
from urllib.parse import urlsplit


NOTICE = re.compile(r'^(licen[cs]e|copying|notice|copyright|authors|ofl|ufl|unlicense)([-._]|$)', re.I)


def pointer_target(data):
    """Recognize a single path to a notice, not prose or known legacy declarations."""
    try:
        value = data.decode('utf-8-sig').strip()
    except UnicodeDecodeError:
        return None
    if len(value) >= 2 and value[0] in ("'", '"') and value[-1] == value[0]:
        value = value[1:-1]
    if not value or len(value) > 4096 or '://' in value or re.search(r'[\r\n\t\x00<>"|?*]', value):
        return None
    path = value.replace('\\', '/')
    parts = path.split('/')
    # These historical declaration forms must not be mistaken for paths.
    if re.fullmatch(r'(?:MIT|Apache-2\.0|Unlicense)(?: */ *(?:MIT|Apache-2\.0|Unlicense))+', value):
        return None
    if (value.startswith(('.', '/', '\\')) or PureWindowsPath(value).drive or
            NOTICE.match(parts[-1]) or
            any(p.lower() in ('license', 'licenses', 'licence', 'licences') for p in parts[:-1]) or
            len(parts) > 1):
        return value
    return None


def relative_target(path, target, root):
    """Normalize lexically with a fixed root, rejecting absolute/drive paths."""
    target = target.replace('\\', '/')
    if PurePosixPath(target).is_absolute() or PureWindowsPath(target).drive:
        raise ValueError('absolute or drive-qualified path')
    boundary = PurePosixPath(root).parts
    parts = list(PurePosixPath(path).parent.parts)
    if tuple(parts[:len(boundary)]) != boundary:
        raise ValueError('source outside approved directory')
    for part in target.split('/'):
        if part == '..':
            if len(parts) <= len(boundary):
                raise ValueError('path escapes approved directory')
            parts.pop()
        elif part not in ('', '.'):
            parts.append(part)
    return '/'.join(parts)


def resolve_pointer(path, contents, recoveries=None):
    """Return a trace for pointer files, or None for ordinary notice text.

    Contents is restricted to this component's distributed notices. Recovery
    mappings are supplied only after pinned-source provenance validation.
    """
    original = pointer_target(contents[path])
    if original is None:
        return None
    result = dict(target=original, status='unresolved', chain=[])
    current = path
    seen = set()
    recovered = False
    while True:
        if current in seen:
            result['reason'] = f'cycle at {current}'
            return result
        seen.add(current)
        if current not in contents:
            result['reason'] = f'missing target: {current}'
            return result
        data = contents[current]
        target = pointer_target(data)
        if target is None:
            if not data.strip():
                result['reason'] = f'empty target: {current}'
                return result
            result.update(status='resolved', resolved_path=current,
                          via='verified-upstream' if recovered else 'included-target')
            return result
        result['chain'].append(current)
        try:
            destination = relative_target(current, target, 'third_party')
        except ValueError as error:
            result['reason'] = f'unsafe target: {error}'
            return result
        if recoveries and current in recoveries:
            destination = recoveries[current]
            # Pure data lookup, still restricted to approved packaged locations.
            if not destination.startswith('third_party/upstream/') or '..' in PurePosixPath(destination).parts:
                result['reason'] = 'unsafe target: recovery outside upstream directory'
                return result
            recovered = True
        current = destination


def verified_recoveries(package, supplements, contents=None):
    """Accept explicit aliases only for the package's recorded GitHub revision."""
    key = package['name'] + '-' + package['version']
    mapping = {}
    for entry in supplements:
        if key not in entry['crates'] or not entry.get('resolves'):
            continue
        revision = entry.get('revision', '')
        recorded = (package.get('upstream_vcs') or {}).get('git', {}).get('sha1')
        repository = urlsplit(package.get('repository') or '')
        repo_parts = repository.path.strip('/').split('/')[:2]
        upstream_path = entry.get('upstream_path', '')
        if (not re.fullmatch(r'[0-9a-f]{40}', revision) or revision != recorded or
                repository.hostname != 'github.com' or len(repo_parts) != 2 or
                not upstream_path or '..' in PurePosixPath(upstream_path).parts or
                PurePosixPath(upstream_path).is_absolute() or '\\' in upstream_path):
            raise ValueError(f'Unverified pointer recovery provenance for {key}')
        expected_url = f"https://raw.githubusercontent.com/{'/'.join(repo_parts)}/{revision}/{upstream_path}"
        if entry['url'] != expected_url:
            raise ValueError(f'Pointer recovery URL does not match recorded source for {key}')
        if (not entry['path'].startswith('third_party/upstream/') or
                '..' in PurePosixPath(entry['path']).parts or '\\' in entry['path']):
            raise ValueError('Unsafe pointer recovery destination')
        prefix = f'third_party/licenses/{key}/'
        for pointer in entry['resolves']:
            if not pointer.startswith(prefix) or '..' in PurePosixPath(pointer).parts or '\\' in pointer:
                raise ValueError(f'Pointer recovery belongs outside {key}')
            if contents is None or pointer not in contents or pointer_target(contents[pointer]) is None:
                raise ValueError('Recovery does not name an included pointer')
            vcs_path = (package.get('upstream_vcs') or {}).get('path_in_vcs', '')
            if PurePosixPath(vcs_path).is_absolute() or '..' in PurePosixPath(vcs_path).parts or '\\' in vcs_path:
                raise ValueError('Unsafe upstream crate path')
            upstream_pointer = '/'.join(p for p in ('upstream', vcs_path, pointer[len(prefix):]) if p)
            expected_target = relative_target(upstream_pointer, pointer_target(contents[pointer]), 'upstream')
            if expected_target != 'upstream/' + upstream_path:
                raise ValueError('Pointer recovery does not match the upstream link target')
            if pointer in mapping and mapping[pointer] != entry['path']:
                raise ValueError(f'Conflicting pointer recoveries for {pointer}')
            mapping[pointer] = entry['path']
    return mapping
