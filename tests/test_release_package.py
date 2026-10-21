import plistlib
import stat
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.package_release import build_package


class ReleasePackageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.binary = self.root / "built" / "pdf-squeeze"
        self.binary.parent.mkdir()
        self.binary.write_bytes(b"test executable")
        (self.root / "README.md").write_text("Project README\n")
        packaging = self.root / "packaging"
        packaging.mkdir()
        for platform in ("WINDOWS", "LINUX", "MACOS"):
            (packaging / f"INSTALL-{platform}.md").write_text(f"{platform} install\n")

    def test_windows_zip_contains_only_executable_and_instructions(self):
        archive = build_package("windows-x64", self.binary, self.root / "dist", "0.1.0", self.root)
        self.assertEqual(archive.name, "pdf-squeeze-windows-x64.zip")
        with zipfile.ZipFile(archive) as package:
            self.assertEqual(set(package.namelist()), {"pdf-squeeze.exe", "README.md", "INSTALL.md"})
            self.assertEqual(package.read("pdf-squeeze.exe"), b"test executable")

    def test_linux_tar_preserves_executable_permission(self):
        archive = build_package("linux-x64", self.binary, self.root / "dist", "0.1.0", self.root)
        self.assertEqual(archive.name, "pdf-squeeze-linux-x64.tar.gz")
        with tarfile.open(archive, "r:gz") as package:
            self.assertEqual(set(package.getnames()), {"pdf-squeeze", "README.md", "INSTALL.md"})
            executable = package.getmember("pdf-squeeze")
            self.assertTrue(executable.mode & stat.S_IXUSR)

    def test_macos_archives_contain_valid_app_bundle(self):
        for platform in ("macos-arm64", "macos-x64"):
            with self.subTest(platform=platform):
                archive = build_package(platform, self.binary, self.root / "dist", "0.1.0", self.root)
                self.assertEqual(archive.name, f"pdf-squeeze-{platform}.zip")
                with zipfile.ZipFile(archive) as package:
                    executable = "PDF Squeeze.app/Contents/MacOS/pdf-squeeze"
                    plist = "PDF Squeeze.app/Contents/Info.plist"
                    self.assertEqual(set(package.namelist()),
                                     {executable, plist, "README.md", "INSTALL.md"})
                    self.assertTrue(package.getinfo(executable).external_attr >> 16 & stat.S_IXUSR)
                    metadata = plistlib.loads(package.read(plist))
                    self.assertEqual(metadata["CFBundleExecutable"], "pdf-squeeze")
                    self.assertEqual(metadata["CFBundlePackageType"], "APPL")
                    self.assertEqual(metadata["CFBundleShortVersionString"], "0.1.0")


if __name__ == "__main__":
    unittest.main()
