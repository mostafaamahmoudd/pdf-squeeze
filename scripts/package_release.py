"""Build the four release archives without bundling Ghostscript."""

import argparse
import json
import plistlib
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path


PLATFORMS = {
    "windows-x64": ("zip", "WINDOWS"),
    "linux-x64": ("tar.gz", "LINUX"),
    "macos-arm64": ("zip", "MACOS"),
    "macos-x64": ("zip", "MACOS"),
}


def build_package(platform: str, binary: Path, out_dir: Path, version: str, repo_root: Path) -> Path:
    """Create one platform archive from the native release executable."""
    if platform not in PLATFORMS:
        raise ValueError(f"unsupported platform: {platform}")
    if not binary.is_file():
        raise FileNotFoundError(binary)

    extension, install_platform = PLATFORMS[platform]
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / f"pdf-squeeze-{platform}.{extension}"
    with tempfile.TemporaryDirectory() as temporary:
        stage = Path(temporary)
        shutil.copy2(repo_root / "README.md", stage / "README.md")
        shutil.copy2(repo_root / "packaging" / f"INSTALL-{install_platform}.md", stage / "INSTALL.md")
        license_file = repo_root / "LICENSE"
        if license_file.is_file():
            shutil.copy2(license_file, stage / "LICENSE")

        if platform.startswith("macos-"):
            contents = stage / "PDF Squeeze.app" / "Contents"
            executable = contents / "MacOS" / "pdf-squeeze"
            executable.parent.mkdir(parents=True)
            shutil.copy2(binary, executable)
            executable.chmod(0o755)
            info = {
                "CFBundleDevelopmentRegion": "en",
                "CFBundleDisplayName": "PDF Squeeze",
                "CFBundleExecutable": "pdf-squeeze",
                "CFBundleIdentifier": "com.mostafaamahmoudd.pdf-squeeze",
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
            if platform == "linux-x64":
                executable.chmod(0o755)

        files = sorted(path for path in stage.rglob("*") if path.is_file())
        if extension == "zip":
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as package:
                for path in files:
                    package.write(path, path.relative_to(stage).as_posix())
        else:
            with tarfile.open(archive, "w:gz") as package:
                for path in files:
                    package.add(path, arcname=path.relative_to(stage).as_posix())
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
