"""Build the four release archives without bundling Ghostscript."""

import argparse
import html
import json
import plistlib
import posixpath
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit


if __package__:
    from .verify_licenses import license_files
else:
    from verify_licenses import license_files


PLATFORMS = {
    "windows-x64": ("zip", "WINDOWS"),
    "linux-x64": ("tar.gz", "LINUX"),
    "macos-arm64": ("zip", "MACOS"),
    "macos-x64": ("zip", "MACOS"),
}


class _ReadmeImages(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.references.extend(value or "" for key, value in attrs if key == "src")


def verify_package_readme(repo_root: Path, archive: Path) -> None:
    """Check inline Markdown/HTML images without extracting files or using the network."""
    is_zip = archive.name.endswith(".zip")
    with (zipfile.ZipFile(archive) if is_zip else tarfile.open(archive, "r:gz")) as package:
        if is_zip:
            names = {info.filename for info in package.infolist()
                     if not info.is_dir() and not stat.S_ISLNK(info.external_attr >> 16)}
            read_file = package.read
        else:
            names = {info.name for info in package.getmembers() if info.isfile()}

            def read_file(name):
                return package.extractfile(name).read()

        readme = read_file("README.md").decode("utf-8")
        images = _ReadmeImages()
        images.feed(readme)
        references = images.references + re.findall(
            r'!\[[^\]]*\]\(\s*<?([^\s)>]+)>?(?:\s+["\'][^"\']*["\'])?\s*\)', readme)
        local_images = set()
        for reference in references:
            link = urlsplit(html.unescape(reference))
            if link.scheme in {"http", "https"}:
                if (link.hostname in {"github.com", "www.github.com", "raw.githubusercontent.com"}
                        and link.path.lower().startswith("/mostafaamahmoudd/rust-pdf-compressor/")):
                    raise ValueError(f"Repository README image must be packaged: {reference}")
                continue
            path = unquote(link.path)
            target = posixpath.normpath(path)
            if (link.scheme or link.netloc or not path or path.startswith("/")
                    or "\\" in path or re.match(r"^[a-zA-Z]:", path)
                    or target in {".", ".."} or target.startswith("../")):
                raise ValueError(f"Unsafe README image path: {reference}")
            if target not in names:
                raise ValueError(f"Missing README image: {target}")
            local_images.add(target)
        selected = "assets/icons/pdf-squeeze-icon.png"
        if selected not in local_images:
            raise ValueError("README must reference the packaged selected icon")
        if read_file(selected) != (repo_root / selected).read_bytes():
            raise ValueError("Packaged README icon differs from the selected source asset")


def build_package(platform: str, binary: Path, out_dir: Path, version: str, repo_root: Path) -> Path:
    """Create one platform archive from the native release executable."""
    if platform not in PLATFORMS:
        raise ValueError(f"unsupported platform: {platform}")
    if not binary.is_file():
        raise FileNotFoundError(binary)

    licensing = license_files(repo_root)
    extension, install_platform = PLATFORMS[platform]
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / f"pdf-squeeze-{platform}.{extension}"
    with tempfile.TemporaryDirectory() as temporary:
        stage = Path(temporary)
        shutil.copy2(repo_root / "README.md", stage / "README.md")
        shutil.copy2(repo_root / "CONTRIBUTING.md", stage / "CONTRIBUTING.md")
        readme_icon = stage / "assets/icons/pdf-squeeze-icon.png"
        readme_icon.parent.mkdir(parents=True)
        shutil.copy2(repo_root / "assets/icons/pdf-squeeze-icon.png", readme_icon)
        shutil.copy2(repo_root / "packaging" / f"INSTALL-{install_platform}.md", stage / "INSTALL.md")
        for path in licensing:
            destination = stage / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(repo_root / path, destination)

        if platform.startswith("macos-"):
            contents = stage / "PDF Squeeze.app" / "Contents"
            executable = contents / "MacOS" / "pdf-squeeze"
            executable.parent.mkdir(parents=True)
            shutil.copy2(binary, executable)
            executable.chmod(0o755)
            resources = contents / "Resources"
            resources.mkdir()
            shutil.copy2(repo_root / "assets/icons/pdf-squeeze.icns", resources / "pdf-squeeze.icns")
            info = {
                "CFBundleDevelopmentRegion": "en",
                "CFBundleDisplayName": "PDF Squeeze",
                "CFBundleExecutable": "pdf-squeeze",
                "CFBundleIdentifier": "com.mostafaamahmoudd.pdf-squeeze",
                "CFBundleIconFile": "pdf-squeeze.icns",
                "CFBundleName": "PDF Squeeze",
                "CFBundlePackageType": "APPL",
                "CFBundleShortVersionString": version,
                "CFBundleVersion": version,
                "NSHighResolutionCapable": True,
            }
            (contents / "Info.plist").write_bytes(plistlib.dumps(info))
        else:
            executable = stage / ("pdf-squeeze.exe" if platform == "windows-x64" else "pdf-squeeze")
            shutil.copy2(binary, executable)
            if platform == "windows-x64":
                shutil.copy2(repo_root / "assets/icons/pdf-squeeze.ico", stage / "pdf-squeeze.ico")
            else:
                executable.chmod(0o755)
                applications = stage / "share" / "applications"
                applications.mkdir(parents=True)
                shutil.copy2(repo_root / "packaging/pdf-squeeze.desktop", applications / "pdf-squeeze.desktop")
                shutil.copytree(repo_root / "assets/icons/hicolor", stage / "share" / "icons" / "hicolor")

        files = sorted(path for path in stage.rglob("*") if path.is_file())
        if extension == "zip":
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as package:
                for path in files:
                    info = zipfile.ZipInfo(path.relative_to(stage).as_posix())
                    info.create_system = 3
                    info.external_attr = (0o100755 if path == executable else 0o100644) << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                    with path.open("rb") as source, package.open(info, "w") as destination:
                        shutil.copyfileobj(source, destination)
        else:
            with tarfile.open(archive, "w:gz") as package:
                for path in files:
                    info = package.gettarinfo(path, arcname=path.relative_to(stage).as_posix())
                    info.mode = 0o755 if path == executable else 0o644
                    with path.open("rb") as source:
                        package.addfile(info, source)
    verify_package_readme(repo_root, archive)
    return archive


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=PLATFORMS, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("dist"))
    parser.add_argument("--version")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    metadata = json.loads(subprocess.check_output(
        ["cargo", "metadata", "--no-deps", "--locked", "--format-version", "1"], cwd=repo_root))
    version = next(package["version"] for package in metadata["packages"]
                   if package["name"] == "pdf-squeeze")
    if args.version and args.version != version:
        parser.error(f"--version {args.version} does not match Cargo package version {version}")
    archive = build_package(args.platform, args.binary, args.out_dir, version, repo_root)
    print(f"Created {archive} ({archive.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
