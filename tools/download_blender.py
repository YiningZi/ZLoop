"""Download the specified official Linux Blender build and verify its SHA-256."""
import argparse
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import urllib.request


def download(url, destination):
    request = urllib.request.Request(url, headers={"User-Agent": "ZLoop-CI"})
    with urllib.request.urlopen(request, timeout=180) as response:
        with destination.open("wb") as output:
            shutil.copyfileobj(response, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, choices=("4.4.3", "5.1.1"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    series = ".".join(args.version.split(".")[:2])
    filename = f"blender-{args.version}-linux-x64.tar.xz"
    base_url = f"https://download.blender.org/release/Blender{series}/"
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / filename
    checksum_path = output_dir / f"blender-{args.version}.sha256"
    download(base_url + checksum_path.name, checksum_path)
    download(base_url + filename, archive_path)
    checksum = None
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == filename:
            checksum = parts[0].lower()
            break
    if checksum is None or not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise ValueError("Missing checksum for the selected Blender build")
    with archive_path.open("rb") as archive_file:
        digest = hashlib.file_digest(archive_file, "sha256").hexdigest()
    if digest != checksum:
        raise ValueError("Blender download checksum mismatch")
    subprocess.run(["tar", "-xf", str(archive_path), "-C", str(output_dir)], check=True)
    executable = output_dir / f"blender-{args.version}-linux-x64" / "blender"
    if not executable.is_file():
        raise FileNotFoundError(executable)
    print(f"Verified Blender {args.version}: {executable}")
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            output.write(f"executable={executable}\n")


if __name__ == "__main__":
    main()
