import configparser
import hashlib
import io
import json
import plistlib
import posixpath
import re
import stat
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

from scripts.package_release import PLATFORMS, build_package
from scripts import package_release
from scripts.verify_licenses import license_files, verify_archive


class ReleasePackageTests(unittest.TestCase):
    def rewrite_archive(self, archive, replacements):
        altered = self.root / ("altered-" + archive.name)
        if archive.name.endswith(".zip"):
            with zipfile.ZipFile(archive) as source, zipfile.ZipFile(altered, "w") as destination:
                for info in source.infolist():
                    data = replacements.get(info.filename, source.read(info.filename))
                    if data is not None:
                        destination.writestr(info, data)
        else:
            with tarfile.open(archive, "r:gz") as source, tarfile.open(altered, "w:gz") as destination:
                for info in source.getmembers():
                    data = replacements.get(info.name, source.extractfile(info).read())
                    if data is not None:
                        info.size = len(data)
                        destination.addfile(info, io.BytesIO(data))
        return altered

    def test_archive_verification_rejects_missing_or_changed_selected_png(self):
        icon = "assets/icons/pdf-squeeze-icon.png"
        for platform in PLATFORMS:
            archive = build_package(platform, self.binary, self.root / "dist", "0.1.0", self.root)
            for replacement in (None, b"different artwork"):
                with self.subTest(platform=platform, replacement=replacement):
                    altered = self.rewrite_archive(archive, {icon: replacement})
                    with self.assertRaisesRegex(ValueError, "Missing README image|differs"):
                        package_release.verify_package_readme(self.root, altered)

    def test_archive_verification_rejects_changed_readme_image_references(self):
        original = (self.root / "README.md").read_text()
        for platform in PLATFORMS:
            archive = build_package(platform, self.binary, self.root / "dist", "0.1.0", self.root)
            for document, error in (
                ("# Missing selected image\n", "must reference"),
                (original + '\n![missing](assets/icons/missing.png)', "Missing README image"),
                (original + '\n<img src="../outside.png">', "Unsafe README image"),
                (original + '\n<img src="https://raw.githubusercontent.com/mostafaamahmoudd/'
                 'rust-pdf-compressor/master/icon.png">', "Repository README image"),
            ):
                with self.subTest(platform=platform, error=error):
                    altered = self.rewrite_archive(archive, {"README.md": document.encode()})
                    with self.assertRaisesRegex(ValueError, error):
                        package_release.verify_package_readme(self.root, altered)

    def test_packaging_rejects_missing_and_unsafe_readme_images(self):
        original = (self.root / "README.md").read_text()
        for reference, error in (
            ("assets/icons/missing.png", "Missing README image"),
            ("../outside.png", "Unsafe README image"),
            ("%2e%2e/outside.png", "Unsafe README image"),
            ("/outside.png", "Unsafe README image"),
            (r"..\outside.png", "Unsafe README image"),
            ("C:/outside.png", "Unsafe README image"),
            ("file:///outside.png", "Unsafe README image"),
            ("//outside/image.png", "Unsafe README image"),
            ("https://raw.githubusercontent.com/mostafaamahmoudd/rust-pdf-compressor/master/icon.png",
             "Repository README image"),
            ("https://github.com/mostafaamahmoudd/rust-pdf-compressor/raw/master/icon.png",
             "Repository README image"),
        ):
            for platform in PLATFORMS:
                with self.subTest(reference=reference, platform=platform):
                    (self.root / "README.md").write_text(original + f'\n<img src="{reference}">\n')
                    with self.assertRaisesRegex(ValueError, error):
                        build_package(platform, self.binary, self.root / "dist", "0.1.0", self.root)

    def test_packaging_checks_markdown_and_single_quoted_html_images(self):
        original = (self.root / "README.md").read_text()
        for markup in ("![missing](assets/icons/missing.png)", "<IMG SRC='assets/icons/missing.png'>"):
            with self.subTest(markup=markup):
                (self.root / "README.md").write_text(original + "\n" + markup)
                with self.assertRaisesRegex(ValueError, "Missing README image"):
                    build_package("windows-x64", self.binary, self.root / "dist", "0.1.0", self.root)

    def test_packaging_accepts_external_documentation_links(self):
        with (self.root / "README.md").open("a") as readme:
            readme.write('\n[Docs](https://example.com/docs)\n'
                         '[Source image](https://raw.githubusercontent.com/mostafaamahmoudd/'
                         'rust-pdf-compressor/master/assets/icons/pdf-squeeze-icon.png)\n'
                         '![Selected icon](assets/icons/pdf-squeeze-icon.png)\n')
        for platform in PLATFORMS:
            with self.subTest(platform=platform):
                archive = build_package(platform, self.binary, self.root / "dist", "0.1.0", self.root)
                self.assertTrue(archive.is_file())

    def test_shipped_readme_and_install_links_resolve_in_every_layout(self):
        repo = Path(__file__).resolve().parent.parent
        for platform in PLATFORMS:
            with self.subTest(platform=platform):
                archive = build_package(platform, self.binary, self.root / "dist", "0.1.0", repo)
                verify_archive(repo, archive)
                if archive.name.endswith(".zip"):
                    with zipfile.ZipFile(archive) as package:
                        members = set(package.namelist())
                        self.assertIn("CONTRIBUTING.md", members)
                        documents = {name: package.read(name).decode("utf-8")
                                     for name in ("README.md", "INSTALL.md", "CONTRIBUTING.md")}
                        self.assertIn("assets/icons/pdf-squeeze-icon.png", members)
                        self.assertEqual(package.read("assets/icons/pdf-squeeze-icon.png"),
                                         (repo / "assets/icons/pdf-squeeze-icon.png").read_bytes())
                else:
                    with tarfile.open(archive, "r:gz") as package:
                        members = set(package.getnames())
                        self.assertIn("CONTRIBUTING.md", members)
                        documents = {name: package.extractfile(name).read().decode("utf-8")
                                     for name in ("README.md", "INSTALL.md", "CONTRIBUTING.md")}
                        self.assertIn("assets/icons/pdf-squeeze-icon.png", members)
                        self.assertEqual(package.extractfile("assets/icons/pdf-squeeze-icon.png").read(),
                                         (repo / "assets/icons/pdf-squeeze-icon.png").read_bytes())
                self.assertIn('src="assets/icons/pdf-squeeze-icon.png"', documents["README.md"])
                for name, document in documents.items():
                    # Cover Markdown links/images and the README's HTML icon.
                    links = re.findall(r'!?\[[^\]]*\]\(([^)]+)\)|\bsrc="([^"]+)"', document)
                    for markdown, html in links:
                        link = urlsplit(markdown or html)
                        if link.scheme or link.netloc or not link.path:
                            continue
                        target = posixpath.normpath(posixpath.join(
                            posixpath.dirname(name), unquote(link.path)))
                        self.assertTrue(target in members, f"Broken link in {platform}/{name}: {target}")

    def test_desktop_launcher_opens_gui_without_claiming_pdf_files(self):
        desktop = configparser.ConfigParser(interpolation=None)
        desktop.read(Path(__file__).resolve().parent.parent / "packaging" / "pdf-squeeze.desktop")
        entry = desktop["Desktop Entry"]
        self.assertEqual(entry["Exec"], "pdf-squeeze")
        self.assertEqual(entry["Terminal"], "false")
        self.assertNotIn("MimeType", entry)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.binary = self.root / "built" / "pdf-squeeze"
        self.binary.parent.mkdir()
        self.binary.write_bytes(b"test executable")
        (self.root / "README.md").write_text(
            '# Project README\n<img src="assets/icons/pdf-squeeze-icon.png" alt="PDF Squeeze">\n')
        (self.root / "CONTRIBUTING.md").write_text("Contributor guide. See [README](README.md).\n")
        (self.root / "Cargo.lock").write_bytes(b"lock fixture\n")
        (self.root / "THIRD_PARTY_NOTICES.md").write_text("Third-party notices\n")
        (self.root / "LICENSING.md").write_text("Unresolved project and asset rights\n")
        third_party = self.root / "third_party"
        (third_party / "licenses/example").mkdir(parents=True)
        (third_party / "licenses/example/LICENSE").write_bytes(b"Upstream copyright\n")
        notice = dict(path="third_party/licenses/example/LICENSE",
                      sha256=hashlib.sha256(b"Upstream copyright\n").hexdigest())
        (third_party / "inventory.json").write_text(json.dumps(dict(
            schema=1, cargo_lock_sha256=hashlib.sha256(b"lock fixture\n").hexdigest(),
            packages=[dict(name="example", version="1", notices=[notice], issues=[])])))
        (third_party / "fonts.json").write_text("[]\n")
        (third_party / "supplemental.json").write_text("[]\n")
        self.license_paths = {"THIRD_PARTY_NOTICES.md", "LICENSING.md", "third_party/inventory.json",
                              "third_party/fonts.json", "third_party/supplemental.json",
                              "third_party/licenses/example/LICENSE"}
        packaging = self.root / "packaging"
        packaging.mkdir()
        for platform in ("WINDOWS", "LINUX", "MACOS"):
            (packaging / f"INSTALL-{platform}.md").write_text(f"{platform} install\n")
        (packaging / "pdf-squeeze.desktop").write_bytes(
            b"[Desktop Entry]\r\nType=Application\r\nExec=pdf-squeeze\r\nIcon=pdf-squeeze\r\n"
        )
        icons = self.root / "assets" / "icons"
        icons.mkdir(parents=True)
        (icons / "pdf-squeeze-icon.png").write_bytes(b"selected README icon")
        (icons / "pdf-squeeze.ico").write_bytes(b"windows icon")
        (icons / "pdf-squeeze.icns").write_bytes(b"macos icon")
        for size in (16, 32, 48, 64, 128, 256, 512):
            destination = icons / "hicolor" / f"{size}x{size}" / "apps"
            destination.mkdir(parents=True)
            (destination / "pdf-squeeze.png").write_bytes(f"{size} icon".encode())

    def test_windows_zip_contains_executable_icons_instructions_and_licenses(self):
        archive = build_package("windows-x64", self.binary, self.root / "dist", "0.1.0", self.root)
        self.assertEqual(archive.name, "pdf-squeeze-windows-x64.zip")
        with zipfile.ZipFile(archive) as package:
            self.assertEqual(set(package.namelist()),
                             {"pdf-squeeze.exe", "pdf-squeeze.ico", "README.md", "INSTALL.md", "CONTRIBUTING.md",
                              "assets/icons/pdf-squeeze-icon.png"} | self.license_paths)
            for name in self.license_paths:
                self.assertTrue(package.read(name).strip())
            self.assertEqual(package.read("pdf-squeeze.exe"), b"test executable")
            self.assertEqual(package.read("pdf-squeeze.ico"), b"windows icon")

    def test_linux_tar_preserves_executable_permission(self):
        archive = build_package("linux-x64", self.binary, self.root / "dist", "0.1.0", self.root)
        self.assertEqual(archive.name, "pdf-squeeze-linux-x64.tar.gz")
        with tarfile.open(archive, "r:gz") as package:
            expected = {"pdf-squeeze", "README.md", "INSTALL.md", "CONTRIBUTING.md",
                        "assets/icons/pdf-squeeze-icon.png",
                        "share/applications/pdf-squeeze.desktop"}
            expected.update(f"share/icons/hicolor/{size}x{size}/apps/pdf-squeeze.png"
                            for size in (16, 32, 48, 64, 128, 256, 512))
            self.assertEqual(set(package.getnames()), expected | self.license_paths)
            for name in self.license_paths:
                self.assertTrue(package.extractfile(name).read().strip())
            executable = package.getmember("pdf-squeeze")
            self.assertTrue(executable.mode & stat.S_IXUSR)
            desktop = package.extractfile("share/applications/pdf-squeeze.desktop").read().decode()
            self.assertIn("Icon=pdf-squeeze", desktop.splitlines())
            self.assertIn("Exec=pdf-squeeze", desktop.splitlines())

    def test_macos_archives_contain_valid_app_bundle(self):
        for platform in ("macos-arm64", "macos-x64"):
            with self.subTest(platform=platform):
                archive = build_package(platform, self.binary, self.root / "dist", "0.1.0", self.root)
                self.assertEqual(archive.name, f"pdf-squeeze-{platform}.zip")
                with zipfile.ZipFile(archive) as package:
                    executable = "PDF Squeeze.app/Contents/MacOS/pdf-squeeze"
                    plist = "PDF Squeeze.app/Contents/Info.plist"
                    icon = "PDF Squeeze.app/Contents/Resources/pdf-squeeze.icns"
                    self.assertEqual(set(package.namelist()),
                                     {executable, plist, icon, "README.md", "INSTALL.md", "CONTRIBUTING.md",
                                      "assets/icons/pdf-squeeze-icon.png"} | self.license_paths)
                    for name in self.license_paths:
                        self.assertTrue(package.read(name).strip())
                    self.assertTrue(package.getinfo(executable).external_attr >> 16 & stat.S_IXUSR)
                    self.assertEqual(package.read(icon), b"macos icon")
                    metadata = plistlib.loads(package.read(plist))
                    self.assertEqual(metadata["CFBundleExecutable"], "pdf-squeeze")
                    self.assertEqual(metadata["CFBundlePackageType"], "APPL")
                    self.assertEqual(metadata["CFBundleShortVersionString"], "0.1.0")
                    self.assertEqual(metadata["CFBundleIconFile"], "pdf-squeeze.icns")

    def test_packaging_rejects_missing_empty_changed_and_stale_licensing(self):
        for path in self.license_paths:
            destination = self.root / path
            original = destination.read_bytes()
            for replacement in (None, b"  \n", b"changed\n"):
                # Only hashed files and JSON have content checks beyond nonemptiness.
                if replacement == b"changed\n" and path in {"THIRD_PARTY_NOTICES.md", "LICENSING.md"}:
                    continue
                with self.subTest(path=path, replacement=replacement):
                    if replacement is None:
                        destination.unlink()
                    else:
                        destination.write_bytes(replacement)
                    with self.assertRaises((ValueError, FileNotFoundError)):
                        build_package("windows-x64", self.binary, self.root / "dist", "0.1.0", self.root)
                    destination.write_bytes(original)
        (self.root / "Cargo.lock").write_bytes(b"new lock\n")
        with self.assertRaises(ValueError):
            build_package("linux-x64", self.binary, self.root / "dist", "0.1.0", self.root)


    def test_publication_requires_project_license_and_resolved_inventory(self):
        with self.assertRaises(FileNotFoundError):
            license_files(self.root, require_publishable=True)
        (self.root / 'LICENSE').write_text('Test owner-approved license\n')
        inventory = self.root / 'third_party/inventory.json'
        content = json.loads(inventory.read_text())
        content['packages'][0]['issues'] = ['Missing upstream license text']
        inventory.write_text(json.dumps(content))
        with self.assertRaisesRegex(ValueError, 'Unresolved'):
            license_files(self.root, require_publishable=True)
        content['packages'][0]['issues'] = []
        inventory.write_text(json.dumps(content))
        self.assertIn('LICENSE', license_files(self.root, require_publishable=True))


    def test_publication_recomputes_pointer_resolution(self):
        from scripts.license_pointers import resolve_pointer
        (self.root / 'LICENSE').write_text('Test fixture only\n')
        inventory = self.root / 'third_party/inventory.json'
        content = json.loads(inventory.read_text())
        path = 'third_party/licenses/example/LICENSE'
        (self.root / path).write_bytes(b'../LICENSE.MIT')
        notice = content['packages'][0]['notices'][0]
        notice['sha256'] = hashlib.sha256(b'../LICENSE.MIT').hexdigest()
        notice['pointer'] = resolve_pointer(path, {path: b'../LICENSE.MIT'})
        content['packages'][0]['issues'] = ['Unresolved license pointer']
        inventory.write_text(json.dumps(content))
        archive = build_package('windows-x64', self.binary, self.root / 'dist', '0.1.0', self.root)
        verify_archive(self.root, archive)
        # Clearing declared issues cannot hide an unresolved pointer.
        content['packages'][0]['issues'] = []
        inventory.write_text(json.dumps(content))
        with self.assertRaisesRegex(ValueError, 'Unresolved license pointer'):
            license_files(self.root, require_publishable=True)
        notice['pointer'] = dict(target='../LICENSE.MIT', status='resolved')
        inventory.write_text(json.dumps(content))
        with self.assertRaisesRegex(ValueError, 'Pointer resolution mismatch'):
            license_files(self.root)


    def test_publication_rejects_nonstandard_direct_and_nested_pointers(self):
        from scripts.license_pointers import resolve_pointer
        (self.root / 'LICENSE').write_text('Test fixture only\n')
        inventory = self.root / 'third_party/inventory.json'
        original = json.loads(inventory.read_text())
        path = 'third_party/licenses/example/LICENSE'
        for data, nested in [(b'legal/terms', None), (b'"./legal notices/LICENSE MIT.txt"', None),
                             (b'./legal/terms', b'other/terms')]:
            with self.subTest(data=data, nested=nested):
                contents = {path: data}
                if nested:
                    contents['third_party/licenses/example/legal/terms'] = nested
                package = dict(original['packages'][0], notices=[], issues=[])
                for name, value in contents.items():
                    destination = self.root / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(value)
                    package['notices'].append(dict(path=name, sha256=hashlib.sha256(value).hexdigest(),
                                                   pointer=resolve_pointer(name, contents)))
                inventory.write_text(json.dumps(dict(original, packages=[package])))
                with self.assertRaisesRegex(ValueError, 'Unresolved license pointer'):
                    license_files(self.root, require_publishable=True)

    def test_archive_verifier_rejects_missing_or_changed_notice(self):
        archive = build_package('windows-x64', self.binary, self.root / 'dist', '0.1.0', self.root)
        verify_archive(self.root, archive)
        altered = self.root / 'altered.zip'
        for replacement in (None, b'altered copyright'):
            with zipfile.ZipFile(archive) as source, zipfile.ZipFile(altered, 'w') as dest:
                for member in source.namelist():
                    data = source.read(member)
                    if member == 'third_party/licenses/example/LICENSE':
                        if replacement is None:
                            continue
                        data = replacement
                    dest.writestr(member, data)
            with self.assertRaises((KeyError, ValueError)):
                verify_archive(self.root, altered)

    def test_verified_project_license_is_preserved_when_present(self):
        (self.root / "LICENSE").write_bytes(b"Test owner-approved license\n")
        archive = build_package("windows-x64", self.binary, self.root / "dist", "0.1.0", self.root)
        with zipfile.ZipFile(archive) as package:
            self.assertEqual(package.read("LICENSE"), b"Test owner-approved license\n")


if __name__ == "__main__":
    unittest.main()
