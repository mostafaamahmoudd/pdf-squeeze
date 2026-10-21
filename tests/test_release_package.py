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
        (packaging / "pdf-squeeze.desktop").write_text(
            "[Desktop Entry]\nType=Application\nExec=pdf-squeeze %f\nIcon=pdf-squeeze\n"
        )
        icons = self.root / "assets" / "icons"
        icons.mkdir(parents=True)
        (icons / "pdf-squeeze.ico").write_bytes(b"windows icon")
        (icons / "pdf-squeeze.icns").write_bytes(b"macos icon")
        for size in (16, 32, 48, 64, 128, 256, 512):
            destination = icons / "hicolor" / f"{size}x{size}" / "apps"
            destination.mkdir(parents=True)
            (destination / "pdf-squeeze.png").write_bytes(f"{size} icon".encode())

    def test_windows_zip_contains_only_executable_and_instructions(self):
        archive = build_package("windows-x64", self.binary, self.root / "dist", "0.1.0", self.root)
        self.assertEqual(archive.name, "pdf-squeeze-windows-x64.zip")
        with zipfile.ZipFile(archive) as package:
            self.assertEqual(set(package.namelist()),
                             {"pdf-squeeze.exe", "pdf-squeeze.ico", "README.md", "INSTALL.md"})
            self.assertEqual(package.read("pdf-squeeze.exe"), b"test executable")
            self.assertEqual(package.read("pdf-squeeze.ico"), b"windows icon")

    def test_linux_tar_preserves_executable_permission(self):
        archive = build_package("linux-x64", self.binary, self.root / "dist", "0.1.0", self.root)
        self.assertEqual(archive.name, "pdf-squeeze-linux-x64.tar.gz")
        with tarfile.open(archive, "r:gz") as package:
            expected = {"pdf-squeeze", "README.md", "INSTALL.md",
                        "share/applications/pdf-squeeze.desktop"}
            expected.update(f"share/icons/hicolor/{size}x{size}/apps/pdf-squeeze.png"
                            for size in (16, 32, 48, 64, 128, 256, 512))
            self.assertEqual(set(package.getnames()), expected)
            executable = package.getmember("pdf-squeeze")
            self.assertTrue(executable.mode & stat.S_IXUSR)
            desktop = package.extractfile("share/applications/pdf-squeeze.desktop").read()
            self.assertIn(b"Icon=pdf-squeeze", desktop)
            self.assertIn(b"Exec=pdf-squeeze %f", desktop)

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
                                     {executable, plist, icon, "README.md", "INSTALL.md"})
                    self.assertTrue(package.getinfo(executable).external_attr >> 16 & stat.S_IXUSR)
                    self.assertEqual(package.read(icon), b"macos icon")
                    metadata = plistlib.loads(package.read(plist))
                    self.assertEqual(metadata["CFBundleExecutable"], "pdf-squeeze")
                    self.assertEqual(metadata["CFBundlePackageType"], "APPL")
                    self.assertEqual(metadata["CFBundleShortVersionString"], "0.1.0")
                    self.assertEqual(metadata["CFBundleIconFile"], "pdf-squeeze.icns")


if __name__ == "__main__":
    unittest.main()
