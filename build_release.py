# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 YiningZi (SeventhSlice)

"""Build a reproducible Blender add-on ZIP using only the Python standard library."""
import argparse
import ast
import hashlib
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parent
PACKAGE_FILES = ("__init__.py", "README_CN.md", "LICENSE")


def package_source(root, name):
    # Keep a single canonical license; copy it into the installed add-on.
    return root / "LICENSE" if name == "LICENSE" else root / "zloop_addon" / name


def package_contents(path):
    # Canonical LF line endings keep Windows and Linux builds identical.
    return path.read_text(encoding="utf-8").encode("utf-8")


def addon_metadata(root=ROOT):
    """Read bl_info without importing bpy or executing the add-on."""
    source = root / "zloop_addon" / "__init__.py"
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "bl_info" for target in node.targets):
                return ast.literal_eval(node.value)
    raise ValueError("Missing bl_info metadata")


def addon_version(root=ROOT):
    version = addon_metadata(root)["version"]
    if len(version) != 3 or any(type(part) is not int or part < 0 for part in version):
        raise ValueError("bl_info.version must contain three non-negative integers")
    return ".".join(map(str, version))


def build_release(output_dir=None, root=ROOT):
    version = addon_version(root)
    output_dir = Path(output_dir) if output_dir is not None else root / "dist"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"ZLoop_Addon_{version}.zip"
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in PACKAGE_FILES:
            source = package_source(root, name)
            contents = package_contents(source)
            if name.endswith(".py"):
                ast.parse(contents, filename=str(source))
            entry = zipfile.ZipInfo(f"zloop_addon/{name}", date_time=(2020, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, contents)

    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("Corrupt release ZIP")
        expected = {f"zloop_addon/{name}" for name in PACKAGE_FILES}
        if set(archive.namelist()) != expected:
            raise ValueError("Unexpected release contents")
        for name in PACKAGE_FILES:
            if archive.read(f"zloop_addon/{name}") != package_contents(package_source(root, name)):
                raise ValueError(f"Release source mismatch: {name}")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    (output_dir / "SHA256SUMS.txt").write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    print(f"Built {output} ({output.stat().st_size} bytes)")
    print(f"SHA256 {digest}")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    build_release(args.output_dir)


if __name__ == "__main__":
    main()
