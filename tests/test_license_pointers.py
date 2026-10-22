import unittest

from scripts.license_pointers import pointer_target, resolve_pointer, verified_recoveries


class LicensePointerTests(unittest.TestCase):
    def test_valid_text_is_not_a_pointer(self):
        for data in (b'MIT License\nCopyright Example\nPermission is granted.', b'MIT OR Apache-2.0', b'MIT/Apache-2.0', b'MIT / Apache-2.0'):
            self.assertIsNone(pointer_target(data))
            self.assertIsNone(resolve_pointer('third_party/pkg/LICENSE', {'third_party/pkg/LICENSE': data}))

    def test_missing_target_is_unresolved_and_bytes_are_unchanged(self):
        data = b'../LICENSE.MIT\r\n'
        contents = {'third_party/pkg/LICENSE': data}
        result = resolve_pointer('third_party/pkg/LICENSE', contents)
        self.assertEqual(result['status'], 'unresolved')
        self.assertIn('missing target', result['reason'])
        self.assertEqual(contents['third_party/pkg/LICENSE'], data)

    def test_resolvable_nested_and_windows_relative_pointers(self):
        contents = {'third_party/pkg/sub/COPYING': b'..\\LICENSE\r\n',
                    'third_party/pkg/LICENSE': b'./legal/LICENSE-MIT',
                    'third_party/pkg/legal/LICENSE-MIT': b'Copyright Example\nPermission notice'}
        result = resolve_pointer('third_party/pkg/sub/COPYING', contents)
        self.assertEqual(result['status'], 'resolved')
        self.assertEqual(result['resolved_path'], 'third_party/pkg/legal/LICENSE-MIT')
        self.assertEqual(result['chain'], ['third_party/pkg/sub/COPYING', 'third_party/pkg/LICENSE'])


    def test_relative_paths_with_spaces_and_nonstandard_target_names(self):
        for pointer, target in [(b'./legal notices/LICENSE MIT.txt', 'third_party/pkg/legal notices/LICENSE MIT.txt'),
                                (b'legal/TERMS', 'third_party/pkg/legal/TERMS'),
                                (b'legal notices/terms', 'third_party/pkg/legal notices/terms'),
                                (b'"./legal notices/LICENSE MIT.txt"', 'third_party/pkg/legal notices/LICENSE MIT.txt')]:
            with self.subTest(pointer=pointer):
                contents = {'third_party/pkg/LICENSE': pointer, target: b'Original notice text\n'}
                result = resolve_pointer('third_party/pkg/LICENSE', contents)
                self.assertIsNotNone(result)
                self.assertEqual(result['status'], 'resolved')
                self.assertEqual(result['resolved_path'], target)


    def test_nested_nonstandard_missing_target_is_not_complete_evidence(self):
        contents = {'third_party/pkg/LICENSE': b'./legal/terms',
                    'third_party/pkg/legal/terms': b'other/terms'}
        result = resolve_pointer('third_party/pkg/LICENSE', contents)
        self.assertEqual(result['status'], 'unresolved')
        self.assertIn('missing target', result['reason'])
        self.assertEqual(len(result['chain']), 2)

    def test_cycles_are_unresolved(self):
        contents = {'third_party/pkg/LICENSE': b'COPYING', 'third_party/pkg/COPYING': b'LICENSE'}
        result = resolve_pointer('third_party/pkg/LICENSE', contents)
        self.assertEqual(result['status'], 'unresolved')
        self.assertIn('cycle', result['reason'])

    def test_escape_and_absolute_targets_are_never_resolved(self):
        for target in (b'../../LICENSE', b'../..\\LICENSE', b'/etc/LICENSE', b'C:\\LICENSE', b'C:LICENSE', b'\\\\host\\LICENSE'):
            with self.subTest(target=target):
                result = resolve_pointer('third_party/pkg/LICENSE', {'third_party/pkg/LICENSE': target})
                self.assertEqual(result['status'], 'unresolved')
                self.assertIn('unsafe target', result['reason'])

    def test_recovery_requires_matching_revision_repository_and_explicit_mapping(self):
        sha = 'a' * 40
        package = dict(name='pkg', version='1', repository='https://github.com/example/pkg',
                       upstream_vcs={'git': {'sha1': sha}, 'path_in_vcs': 'crate'})
        entry = dict(crates=['pkg-1'], path='third_party/upstream/pkg/LICENSE',
                     revision=sha, upstream_path='LICENSE',
                     url=f'https://raw.githubusercontent.com/example/pkg/{sha}/LICENSE',
                     resolves=['third_party/licenses/pkg-1/LICENSE'])
        pointer_bytes = {'third_party/licenses/pkg-1/LICENSE': b'../LICENSE'}
        mapping = verified_recoveries(package, [entry], pointer_bytes)
        self.assertEqual(mapping, {'third_party/licenses/pkg-1/LICENSE': 'third_party/upstream/pkg/LICENSE'})
        for field, wrong in [('revision', 'b' * 40), ('url', entry['url'].replace('/example/', '/unrelated/')),
                             ('path', '../../LICENSE'), ('resolves', ['third_party/licenses/other-1/LICENSE'])]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                verified_recoveries(package, [dict(entry, **{field: wrong})], pointer_bytes)
        with self.assertRaisesRegex(ValueError, 'upstream link target'):
            verified_recoveries(package, [dict(entry, upstream_path='unrelated/LICENSE',
                url=f'https://raw.githubusercontent.com/example/pkg/{sha}/unrelated/LICENSE')], pointer_bytes)
        contents = {'third_party/licenses/pkg-1/LICENSE': b'../LICENSE',
                    'third_party/upstream/pkg/LICENSE': b'Original permission text\n'}
        result = resolve_pointer('third_party/licenses/pkg-1/LICENSE', contents, mapping)
        self.assertEqual(result['status'], 'resolved')
        self.assertEqual(result['via'], 'verified-upstream')
        contents.pop('third_party/upstream/pkg/LICENSE')
        self.assertEqual(resolve_pointer('third_party/licenses/pkg-1/LICENSE', contents, mapping)['status'], 'unresolved')


if __name__ == '__main__':
    unittest.main()
