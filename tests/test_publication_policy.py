"""Exercise the publication boundary with a small, independently specified graph."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.verify_licenses import license_files, verify_archive
from scripts.package_release import build_package


class PublicationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for path, data in {
            'Cargo.lock': 'locked', 'Cargo.toml': 'manifest', 'src/gs.rs': 'external process',
            'build.rs': 'build', 'LICENSE': 'owner license', 'LICENSING.md': 'review',
            'THIRD_PARTY_NOTICES.md': 'notices', 'third_party/fonts.json': '[]',
            'third_party/supplemental.json': '[]',
            'third_party/licenses/example/LICENSE': 'MIT copyright and terms',
        }.items():
            dest = self.root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(data)
        self.inventory = dict(schema=1, cargo_lock_sha256=self.sha('Cargo.lock'), packages=[
            dict(name='example', version='1.0.0', license='MIT', issues=[], notices=[dict(
                path='third_party/licenses/example/LICENSE',
                sha256=self.sha('third_party/licenses/example/LICENSE'))]),
            dict(name='mac-only', version='2.0.0', license='MIT',
                 issues=['Missing authoritative terms'], notices=[]),
        ])
        self.save_inventory()
        self.policy = dict(schema=1, inputs={p: self.sha(p) for p in (
            'Cargo.lock', 'Cargo.toml', 'src/gs.rs', 'build.rs', 'third_party/inventory.json',
            'third_party/fonts.json', 'third_party/supplemental.json')},
            license_choices={'MIT': 'MIT'}, platforms={
                'windows-x64': dict(target='x86_64-pc-windows-msvc', packages=['example 1.0.0'],
                                    inspection_trees={'linux': ['example 1.0.0'], 'win32': ['example 1.0.0']}),
                'linux-x64': dict(target='x86_64-unknown-linux-gnu', packages=['example 1.0.0'],
                                  inspection_trees={'linux': ['example 1.0.0'], 'win32': ['example 1.0.0']})})
        self.save_policy()
        # Cargo is the external boundary; the inventory, policy and verification are real.
        self.cargo = patch('scripts.publication_policy.subprocess.check_output',
                           return_value='pdf-squeeze v0.1.0 (/checkout)\nexample v1.0.0\n')

    def sha(self, path):
        return hashlib.sha256((self.root / path).read_bytes()).hexdigest()

    def save_inventory(self):
        (self.root / 'third_party/inventory.json').write_text(json.dumps(self.inventory))

    def save_policy(self):
        (self.root / 'third_party/publication-policy.json').write_text(json.dumps(self.policy))

    def verify(self, platform='windows-x64'):
        return license_files(self.root, require_publishable=True, platform=platform)

    def test_inactive_gaps_preserved_and_global_mode_still_rejects(self):
        with self.cargo:
            self.assertIn('LICENSE', self.verify())
            self.assertIn('LICENSE', self.verify('linux-x64'))
        self.assertEqual(self.inventory['packages'][1]['issues'], ['Missing authoritative terms'])
        with self.assertRaisesRegex(ValueError, 'Unresolved'):
            license_files(self.root, require_publishable=True)

    def test_host_build_dependencies_remain_obligations_in_cross_host_review(self):
        self.inventory['packages'].append(dict(name='host-build', version='1.0.0',
            license='MIT', issues=[], notices=self.inventory['packages'][0]['notices']))
        self.save_inventory()
        self.policy['inputs']['third_party/inventory.json'] = self.sha('third_party/inventory.json')
        scope = self.policy['platforms']['windows-x64']
        scope['packages'] = ['example 1.0.0', 'host-build 1.0.0']
        scope['inspection_trees']['win32'] = scope['packages']
        self.save_policy()
        with patch('sys.platform', 'linux'), self.cargo:
            self.assertIn('LICENSE', self.verify())
        with patch('sys.platform', 'win32'), patch(
                'scripts.publication_policy.subprocess.check_output',
                return_value='pdf-squeeze v0.1.0 (/checkout)\nexample v1.0.0\nhost-build v1.0.0\n'):
            self.assertIn('LICENSE', self.verify())
        self.inventory['packages'][-1]['issues'] = ['Unfulfilled build dependency obligation']
        self.save_inventory()
        self.policy['inputs']['third_party/inventory.json'] = self.sha('third_party/inventory.json')
        self.save_policy()
        with patch('sys.platform', 'linux'), self.cargo:
            with self.assertRaisesRegex(ValueError, 'Unresolved active'):
                self.verify()

    def test_unsupported_platforms_fail_closed(self):
        for platform in ('macos-arm64', 'macos-x64', 'unknown'):
            with self.subTest(platform=platform), self.cargo:
                with self.assertRaisesRegex(ValueError, 'not approved'):
                    self.verify(platform)

    def test_changed_review_inputs_fail_closed(self):
        for path in self.policy['inputs']:
            original = (self.root / path).read_bytes()
            (self.root / path).write_bytes(original + b' ')
            with self.subTest(path=path), self.cargo:
                with self.assertRaises(ValueError):
                    self.verify()
            (self.root / path).write_bytes(original)

    def test_changed_tree_and_unknown_packages_fail_closed(self):
        for tree in ('pdf-squeeze v0.1.0 (/checkout)\n',
                     'pdf-squeeze v0.1.0 (/checkout)\nexample v1.0.0\nmac-only v2.0.0\n',
                     'pdf-squeeze v0.1.0 (/checkout)\nexample v9.0.0\n'):
            with self.subTest(tree=tree), patch(
                    'scripts.publication_policy.subprocess.check_output', return_value=tree):
                with self.assertRaisesRegex(ValueError, 'tree'):
                    self.verify()

    def test_active_issues_and_missing_terms_cannot_be_waived(self):
        for change in ({'issues': ['Missing permission']}, {'notices': []}, {'license': 'AGPL-3.0-only'}):
            original = self.inventory['packages'][0].copy()
            self.inventory['packages'][0].update(change)
            self.save_inventory()
            self.policy['inputs']['third_party/inventory.json'] = self.sha('third_party/inventory.json')
            self.save_policy()
            with self.subTest(change=change), self.cargo:
                with self.assertRaises(ValueError):
                    self.verify()
            self.inventory['packages'][0] = original

    def test_active_pointer_cannot_be_hidden_by_empty_issues(self):
        from scripts.license_pointers import resolve_pointer
        path = 'third_party/licenses/example/LICENSE'
        (self.root / path).write_text('../LICENSE.MIT')
        notice = self.inventory['packages'][0]['notices'][0]
        notice.update(sha256=self.sha(path), pointer=resolve_pointer(path, {path: b'../LICENSE.MIT'}))
        self.save_inventory()
        self.policy['inputs']['third_party/inventory.json'] = self.sha('third_party/inventory.json')
        self.save_policy()
        with self.cargo, self.assertRaisesRegex(ValueError, 'Unresolved license pointer'):
            self.verify()

    def test_all_notices_still_checked_including_inactive_evidence(self):
        path = 'third_party/licenses/example/LICENSE'
        (self.root / path).write_text('changed notice')
        with self.cargo, self.assertRaisesRegex(ValueError, 'Notice checksum mismatch'):
            self.verify()

    def test_missing_project_license_still_blocks(self):
        (self.root / 'LICENSE').unlink()
        with self.cargo, self.assertRaises(FileNotFoundError):
            self.verify()

    def test_scope_requires_publication_mode(self):
        with self.cargo, self.assertRaisesRegex(ValueError, 'require_publishable'):
            license_files(self.root, platform='windows-x64')

    def test_archive_scope_must_match_platform(self):
        with self.cargo, self.assertRaisesRegex(ValueError, 'Archive.*platform'):
            verify_archive(self.root, self.root / 'pdf-squeeze-macos-arm64.zip',
                           require_publishable=True, platform='windows-x64')
