import json
import hashlib
import struct
import tempfile
import unittest
from pathlib import Path, PurePath
from unittest.mock import patch

from scripts.license_inventory import collect, write_or_check, dependency_roles


class LicenseInventoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / 'Cargo.lock').write_text('locked fixture\n')
        (self.root / 'third_party').mkdir()
        (self.root / 'third_party/supplemental.json').write_text('[]\n')
        crate = self.root / 'source'
        crate.mkdir()
        (crate / 'Cargo.toml').write_text('[package]\nname="example"\n')
        (crate / 'LICENSE').write_bytes(b'Copyright Example\r\nPermission notice\r\n')
        (crate / 'fonts').mkdir()
        (crate / 'fonts/Hack-Regular.txt').write_bytes(b'Additional font copyright\n')
        self.metadata = {'packages': [dict(id='example 1', name='example', version='1.0.0',
            source='registry+https://github.com/rust-lang/crates.io-index',
            manifest_path=str(crate / 'Cargo.toml'), license='MIT OR Apache-2.0',
            license_file=None, repository='https://example.test', authors=['Example'],
            targets=[])], 'resolve': {'root': 'app', 'nodes': []}}

    def test_preserves_notice_bytes_and_declared_expression(self):
        files = collect(self.root, self.metadata, {})
        self.assertEqual(files['third_party/licenses/example-1.0.0/LICENSE'],
                         b'Copyright Example\r\nPermission notice\r\n')
        self.assertEqual(files['third_party/licenses/example-1.0.0/fonts/Hack-Regular.txt'],
                         b'Additional font copyright\n')
        inventory = json.loads(files['third_party/inventory.json'])
        self.assertEqual(inventory['packages'][0]['license'], 'MIT OR Apache-2.0')
        self.assertEqual(inventory['packages'][0]['issues'], [])

    def test_missing_license_text_is_explicit(self):
        (self.root / 'source/LICENSE').unlink()
        (self.root / 'source/fonts/Hack-Regular.txt').unlink()
        inventory = json.loads(collect(self.root, self.metadata, {})['third_party/inventory.json'])
        self.assertIn('No license or notice text found', inventory['packages'][0]['issues'])

    def test_check_detects_missing_stale_and_extra_files_without_writing(self):
        expected = {'third_party/licenses/a/LICENSE': b'copyright\n'}
        write_or_check(self.root, expected, check=False)
        self.assertTrue(write_or_check(self.root, expected, check=True))
        notice = self.root / 'third_party/licenses/a/LICENSE'
        notice.write_bytes(b'changed\n')
        self.assertFalse(write_or_check(self.root, expected, check=True))
        self.assertEqual(notice.read_bytes(), b'changed\n')
        notice.unlink()
        self.assertFalse(write_or_check(self.root, expected, check=True))
        write_or_check(self.root, expected, check=False)
        (notice.parent / 'OLD').write_text('old')
        self.assertFalse(write_or_check(self.root, expected, check=True))






    def test_vcs_symlink_cannot_supply_recovery_provenance(self):
        vcs = self.root / 'source/.cargo_vcs_info.json'
        vcs.write_text('{"git": {"sha1": "untrusted"}}')
        original = Path.is_symlink
        with patch.object(Path, 'is_symlink', lambda path: path == vcs or original(path)):
            with self.assertRaisesRegex(ValueError, 'Unsafe upstream VCS'):
                collect(self.root, self.metadata, {})

    def test_pointer_targets_are_copied_and_resolved_in_distribution(self):
        original = b'./legal/terms.txt\r\n'
        (self.root / 'source/LICENSE').write_bytes(original)
        legal = self.root / 'source/legal'
        legal.mkdir()
        (legal / 'terms.txt').write_bytes(b'Original upstream permission text\n')
        files = collect(self.root, self.metadata, {})
        package = json.loads(files['third_party/inventory.json'])['packages'][0]
        notice = next(n for n in package['notices'] if n['path'].endswith('/LICENSE'))
        self.assertEqual(notice['pointer']['status'], 'resolved')
        self.assertEqual(notice['pointer']['resolved_path'], 'third_party/licenses/example-1.0.0/legal/terms.txt')
        self.assertEqual(files['third_party/licenses/example-1.0.0/LICENSE'], original)
        self.assertEqual(files['third_party/licenses/example-1.0.0/legal/terms.txt'], b'Original upstream permission text\n')
        self.assertEqual(package['issues'], [])

    def test_missing_pointer_is_an_issue_even_with_other_notices(self):
        (self.root / 'source/LICENSE').write_bytes(b'../LICENSE.MIT')
        files = collect(self.root, self.metadata, {})
        package = json.loads(files['third_party/inventory.json'])['packages'][0]
        self.assertTrue(any('Unresolved license pointer' in issue for issue in package['issues']))
        notice = next(n for n in package['notices'] if n['path'].endswith('/LICENSE'))
        self.assertEqual(notice['pointer']['status'], 'unresolved')
        self.assertEqual(files['third_party/licenses/example-1.0.0/LICENSE'], b'../LICENSE.MIT')

    def test_pointer_escape_does_not_read_or_copy_outside_source(self):
        (self.root / 'source/LICENSE').write_bytes(b'../LICENSE.MIT')
        (self.root / 'LICENSE.MIT').write_bytes(b'UNRELATED PRIVATE CONTENT')
        original_read = Path.read_bytes
        outside = self.root / 'LICENSE.MIT'
        def guarded_read(path):
            self.assertNotEqual(path, outside, 'Generator tried to read outside the crate source')
            return original_read(path)
        with patch.object(Path, 'read_bytes', guarded_read):
            files = collect(self.root, self.metadata, {})
        self.assertFalse(any(b'UNRELATED PRIVATE CONTENT' in data for data in files.values()))
        package = json.loads(files['third_party/inventory.json'])['packages'][0]
        self.assertTrue(any('Unresolved license pointer' in issue for issue in package['issues']))

    def test_ordinary_source_code_is_not_a_license_notice(self):
        (self.root / 'source/LICENSE').unlink()
        (self.root / 'source/fonts/Hack-Regular.txt').unlink()
        source = self.root / 'source/src'
        source.mkdir()
        (source / 'copying.rs').write_text('fn copy_object() {}\n')
        package = json.loads(collect(self.root, self.metadata, {})['third_party/inventory.json'])['packages'][0]
        self.assertEqual(package['notices'], [])
        self.assertIn('No license or notice text found', package['issues'])

    def test_notice_order_is_identical_with_windows_path_comparison(self):
        (self.root / 'source/LICENSE-z').write_text('Uppercase filename notice')
        (self.root / 'source/license-a').write_text('Lowercase filename notice')
        # Windows paths compare case-insensitively. Generation must order by
        # portable relative strings so checked-in bytes match on every runner.
        with patch.object(PurePath, '__lt__', lambda left, right: left.as_posix().casefold() < right.as_posix().casefold()):
            files = collect(self.root, self.metadata, {})
        notices = json.loads(files['third_party/inventory.json'])['packages'][0]['notices']
        self.assertEqual([n['path'] for n in notices], [
            'third_party/licenses/example-1.0.0/LICENSE',
            'third_party/licenses/example-1.0.0/LICENSE-z',
            'third_party/licenses/example-1.0.0/fonts/Hack-Regular.txt',
            'third_party/licenses/example-1.0.0/license-a',
        ])

    def test_supplement_checksum_tampering_is_rejected(self):
        path = self.root / 'third_party/upstream/example/LICENSE'
        path.parent.mkdir(parents=True)
        path.write_bytes(b'original notice')
        entry = dict(crates=['example-1.0.0'], path='third_party/upstream/example/LICENSE',
                     url='https://example.test/pinned/LICENSE',
                     sha256=hashlib.sha256(b'original notice').hexdigest(),
                     issues=['Scope notice only; full text not recovered'])
        (self.root / 'third_party/supplemental.json').write_text(json.dumps([entry]))
        self.assertEqual(len(json.loads(collect(self.root, self.metadata, {})[
            'third_party/inventory.json'])['packages'][0]['notices']), 3)
        package = json.loads(collect(self.root, self.metadata, {})['third_party/inventory.json'])['packages'][0]
        self.assertIn('Scope notice only; full text not recovered', package['issues'])
        path.write_bytes(b'changed notice')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            collect(self.root, self.metadata, {})

    def test_extracts_original_font_copyright_text_and_bytes(self):
        from scripts.license_inventory import font_names
        copyright_bytes = 'Copyright Example Font'.encode('utf-16-be')
        names = struct.pack('>HHH', 0, 1, 18) + struct.pack('>HHHHHH', 3, 1, 1033, 0, len(copyright_bytes), 0) + copyright_bytes
        font = struct.pack('>IHHHH', 0x10000, 1, 0, 0, 0) + struct.pack('>4sIII', b'name', 0, 28, len(names)) + names
        records = font_names(font)
        self.assertEqual(records[0]['text'], 'Copyright Example Font')
        self.assertEqual(records[0]['raw_hex'], copyright_bytes.hex())

    def test_tracks_build_paths_proc_macros_and_target_edges(self):
        def dep(package, kind=None):
            return {'pkg': package, 'dep_kinds': [{'kind': kind, 'target': None}]}
        def node(id, deps):
            return {'id': id, 'deps': deps}
        metadata = {'packages': [{'id': 'macro', 'targets': [{'kind': ['proc-macro']}]}],
            'resolve': {'root': 'app', 'nodes': [
                node('app', [dep('runtime'), dep('builder', 'build'), dep('macro'), dep('test', 'dev')]),
                node('runtime', [dep('shared')]), node('builder', [dep('shared')]),
                node('macro', [dep('macro-helper')])]}}
        roles = dependency_roles(metadata)
        self.assertEqual(roles['runtime'], ['normal'])
        self.assertEqual(roles['builder'], ['build'])
        self.assertEqual(roles['shared'], ['build', 'normal'])
        self.assertEqual(roles['macro-helper'], ['build'])
        self.assertNotIn('test', roles)


if __name__ == '__main__':
    unittest.main()
