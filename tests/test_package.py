# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 YiningZi (SeventhSlice)

"""Validate distributable content, reproducibility, versioning and release notes."""
import hashlib
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build_release import addon_version, build_release, PACKAGE_FILES
from tools.release_notes import extract_notes, validate_release_version


class PackageTests(unittest.TestCase):
    def test_clean_installable_package_and_checksum(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = build_release(Path(temporary))
            with zipfile.ZipFile(path) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(set(archive.namelist()),
                                 {f"zloop_addon/{name}" for name in PACKAGE_FILES})
                self.assertEqual(archive.read("zloop_addon/__init__.py"),
                                 (ROOT / "zloop_addon/__init__.py").read_text(encoding="utf-8").encode("utf-8"))
                self.assertEqual(archive.read("zloop_addon/LICENSE"),
                                 (ROOT / "LICENSE").read_text(encoding="utf-8").encode("utf-8"))
                self.assertIn(b"GNU GENERAL PUBLIC LICENSE", archive.read("zloop_addon/LICENSE"))
                self.assertIn(b"SPDX-License-Identifier: GPL-3.0-or-later",
                              archive.read("zloop_addon/__init__.py"))
            expected = f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
            self.assertEqual((path.parent / "SHA256SUMS.txt").read_text(encoding="utf-8"), expected)

    def test_repeated_build_is_identical(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = build_release(Path(temporary) / "one").read_bytes()
            second = build_release(Path(temporary) / "two").read_bytes()
            self.assertEqual(first, second)

    def test_build_uses_metadata_and_excludes_extra_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "zloop_addon"
            package.mkdir()
            (package / "__init__.py").write_text(
                'bl_info = {"version": (3, 7, 9), "blender": (4, 4, 0)}\n', encoding="utf-8")
            shutil.copyfile(ROOT / "zloop_addon/README_CN.md", package / "README_CN.md")
            shutil.copyfile(ROOT / "LICENSE", root / "LICENSE")
            (package / "__pycache__").mkdir()
            (package / "__pycache__/old.pyc").write_bytes(b"stale cache")
            (package / "private.txt").write_text("exclude from package", encoding="utf-8")
            output = build_release(root=root)
            self.assertEqual(output.name, "ZLoop_Addon_3.7.9.zip")
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(len(archive.namelist()), 3)

    def test_changelog_covers_historical_versions(self):
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        for version in ("2.0.0", "2.1.0", "2.2.0", addon_version()):
            notes = extract_notes(changelog, version)
            self.assertTrue(notes.strip())
            self.assertNotIn("## [Unreleased]", notes)
            self.assertNotIn("## [", notes)

    def test_current_version_matches_user_documentation(self):
        version = addon_version()
        self.assertIn(f"**{version}**", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertTrue((ROOT / "zloop_addon/README_CN.md").read_text(encoding="utf-8")
                        .startswith(f"# ZLoop 环线工具 {version}"))

    def test_release_rejects_wrong_tag_and_missing_notes(self):
        validate_release_version(f"v{addon_version()}", addon_version())
        with self.assertRaises(ValueError):
            validate_release_version("v99.0.0", addon_version())
        with self.assertRaises(ValueError):
            extract_notes("## [Unreleased]\nnext changes\n", addon_version())
        with self.assertRaises(ValueError):
            extract_notes("## [2.2.0]\n", "2.2.0")
        with self.assertRaises(ValueError):
            extract_notes("## [2.2.0]\none\n## [2.2.0]\ntwo\n", "2.2.0")


if __name__ == "__main__":
    unittest.main()
