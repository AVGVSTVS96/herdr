import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SPEC = importlib.util.spec_from_file_location(
    "fork_sync", Path(__file__).with_name("fork_sync.py")
)
fork_sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fork_sync)


def new_file_diff(path: str) -> str:
    return (
        f"diff --git a/{path} b/{path}\n"
        "new file mode 100644\n"
        "index 0000000..7898192\n"
        "--- /dev/null\n"
        f"+++ b/{path}\n"
        "@@ -0,0 +1 @@\n"
        "+content\n"
    )


def fake_diff_git(changed_paths: list[str]):
    """Stand-in for fork_sync.git covering the diff calls refresh makes."""

    def fake_git(*args, text=True):
        if "--name-only" in args:
            return SimpleNamespace(stdout="".join(f"{p}\n" for p in changed_paths))
        paths = args[args.index("--") + 1 :]
        diff = "".join(new_file_diff(p) for p in paths if p in changed_paths)
        return SimpleNamespace(stdout=diff.encode())

    return fake_git


def write_patch_package(
    patches: Path,
    patch_id: str,
    changed_path: str,
    *,
    baseline: str = "a" * 40,
) -> Path:
    directory = patches / patch_id
    directory.mkdir()
    patch = directory / f"{patch_id}.patch"
    patch.write_text(
        f"""diff --git a/{changed_path} b/{changed_path}
new file mode 100644
index 0000000..7898192
--- /dev/null
+++ b/{changed_path}
@@ -0,0 +1 @@
+content
"""
    )
    (directory / "PATCH.md").write_text(
        f"""---
format: patch-md/v0.1
id: {patch_id}
summary: Test patch.
baseline: {baseline}
patch_file: {patch.name}
patch_sha256: {fork_sync.sha256(patch)}
---

## Intent

Test.

## Verification

Test.

## Removal

Test.
"""
    )
    return patch


class ForkSyncTests(unittest.TestCase):
    def test_stable_manifest_contains_checksummed_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = root / "assets"
            assets.mkdir()
            for name in (
                "herdr-linux-x86_64",
                "herdr-linux-aarch64",
                "herdr-macos-x86_64",
                "herdr-macos-aarch64",
            ):
                (assets / name).write_bytes(name.encode())
            output = root / "latest.json"
            args = SimpleNamespace(
                channel="stable",
                version="0.7.5",
                protocol=17,
                tag="patched-v0.7.5",
                repository="owner/herdr",
                asset_dir=str(assets),
                output=str(output),
                notes="Patched release",
                source_sha="a" * 40,
                build_id="",
                built_at="",
            )

            fork_sync.write_manifest(args)

            manifest = json.loads(output.read_text())
            asset = manifest["assets"]["macos-aarch64"]
            self.assertEqual(
                asset["url"],
                "https://github.com/owner/herdr/releases/download/"
                "patched-v0.7.5/herdr-macos-aarch64",
            )
            self.assertEqual(len(asset["sha256"]), 64)
            self.assertIn("0.7.5", manifest["releases"])

    def test_preview_manifest_retains_only_unexpired_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = root / "assets"
            assets.mkdir()
            for name in (
                "herdr-linux-x86_64",
                "herdr-linux-aarch64",
                "herdr-macos-x86_64",
                "herdr-macos-aarch64",
            ):
                (assets / name).write_bytes(name.encode())
            output = root / "preview.json"
            output.write_text(
                json.dumps(
                    {
                        "builds": {
                            "recent": {
                                "commit": "recent",
                                "built_at": "2026-07-20T00:00:00Z",
                            },
                            "expired": {
                                "commit": "expired",
                                "built_at": "2026-07-01T00:00:00Z",
                            },
                            "undated": {"commit": "undated"},
                        }
                    }
                )
            )
            args = SimpleNamespace(
                channel="preview",
                version="0.7.6",
                protocol=18,
                tag="patched-preview-2026-07-23-abcdef",
                repository="owner/herdr",
                asset_dir=str(assets),
                output=str(output),
                notes="Patched preview",
                source_sha="b" * 40,
                build_id="2026-07-23-abcdef",
                built_at="2026-07-23T00:00:00Z",
            )

            fork_sync.write_manifest(args)

            manifest = json.loads(output.read_text())
            self.assertIn("recent", manifest["builds"])
            self.assertNotIn("expired", manifest["builds"])
            self.assertNotIn("undated", manifest["builds"])
            self.assertEqual(
                manifest["builds"]["2026-07-23-abcdef"]["commit"], "b" * 40
            )

    def test_validate_rejects_duplicate_claimed_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            patches = Path(tmp)
            for patch_id in ("one", "two"):
                write_patch_package(patches, patch_id, "same.rs")

            with mock.patch.object(fork_sync, "PATCHES_DIR", patches):
                with self.assertRaisesRegex(SystemExit, "changed by both"):
                    fork_sync.validate()

    def test_validate_reads_external_patch_from_patch_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            patches = Path(tmp)
            patch_path = write_patch_package(patches, "one", "src/one.rs")

            with mock.patch.object(fork_sync, "PATCHES_DIR", patches):
                specs = fork_sync.validate()

            self.assertEqual(len(specs), 1)
            self.assertEqual(specs[0].patch_id, "one")
            self.assertEqual(specs[0].patch_path, patch_path)
            self.assertEqual(specs[0].paths, ("src/one.rs",))

    def test_patch_paths_includes_both_sides_of_rename(self):
        with tempfile.TemporaryDirectory() as tmp:
            patch = Path(tmp) / "rename.patch"
            patch.write_text(
                """diff --git a/old.txt b/new.txt
similarity index 100%
rename from old.txt
rename to new.txt
"""
            )

            self.assertEqual(
                fork_sync.patch_paths(patch),
                ("new.txt", "old.txt"),
            )

    def test_validate_rejects_patch_checksum_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            patches = Path(tmp)
            patch_path = write_patch_package(patches, "one", "src/one.rs")
            patch_path.write_text(patch_path.read_text() + "\n")

            with mock.patch.object(fork_sync, "PATCHES_DIR", patches):
                with self.assertRaisesRegex(SystemExit, "checksum mismatch"):
                    fork_sync.validate()

    def test_validate_rejects_extra_package_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            patches = Path(tmp)
            write_patch_package(patches, "one", "src/one.rs")
            (patches / "one" / "meta.json").write_text("{}\n")

            with mock.patch.object(fork_sync, "PATCHES_DIR", patches):
                with self.assertRaisesRegex(SystemExit, "unexpected files"):
                    fork_sync.validate()

    def test_validate_rejects_different_baselines(self):
        with tempfile.TemporaryDirectory() as tmp:
            patches = Path(tmp)
            write_patch_package(patches, "one", "src/one.rs")
            write_patch_package(
                patches,
                "two",
                "src/two.rs",
                baseline="b" * 40,
            )

            with mock.patch.object(fork_sync, "PATCHES_DIR", patches):
                with self.assertRaisesRegex(SystemExit, "same baseline"):
                    fork_sync.validate()

    def test_refresh_sweeps_unassigned_paths_into_overflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            patches = Path(tmp)
            write_patch_package(patches, "one", "src/one.rs")

            with (
                mock.patch.object(fork_sync, "PATCHES_DIR", patches),
                mock.patch.object(
                    fork_sync,
                    "git",
                    fake_diff_git(["src/one.rs", "src/extra.rs"]),
                ),
            ):
                fork_sync.refresh(SimpleNamespace(source_sha="b" * 40))
                specs = {spec.patch_id: spec for spec in fork_sync.validate()}

            self.assertEqual(specs["one"].paths, ("src/one.rs",))
            self.assertEqual(specs["one"].baseline, "b" * 40)
            overflow = specs["heal-overflow"]
            self.assertEqual(overflow.paths, ("src/extra.rs",))
            self.assertEqual(overflow.baseline, "b" * 40)

    def test_refresh_removes_overflow_once_paths_are_assigned(self):
        with tempfile.TemporaryDirectory() as tmp:
            patches = Path(tmp)
            write_patch_package(patches, "one", "src/one.rs")
            write_patch_package(patches, "heal-overflow", "src/extra.rs")

            with (
                mock.patch.object(fork_sync, "PATCHES_DIR", patches),
                mock.patch.object(
                    fork_sync, "git", fake_diff_git(["src/one.rs"])
                ),
            ):
                fork_sync.refresh(SimpleNamespace(source_sha="b" * 40))

            self.assertFalse((patches / "heal-overflow").exists())

    def test_refresh_keeps_still_unassigned_overflow_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            patches = Path(tmp)
            write_patch_package(patches, "one", "src/one.rs")
            write_patch_package(patches, "heal-overflow", "src/extra.rs")

            with (
                mock.patch.object(fork_sync, "PATCHES_DIR", patches),
                mock.patch.object(
                    fork_sync,
                    "git",
                    fake_diff_git(["src/one.rs", "src/extra.rs"]),
                ),
            ):
                fork_sync.refresh(SimpleNamespace(source_sha="b" * 40))
                specs = {spec.patch_id: spec for spec in fork_sync.validate()}

            self.assertEqual(specs["heal-overflow"].paths, ("src/extra.rs",))

    def test_verify_changed_paths_ignores_control_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            patches = Path(tmp)
            write_patch_package(patches, "one", "src/one.rs")

            with (
                mock.patch.object(fork_sync, "PATCHES_DIR", patches),
                mock.patch.object(
                    fork_sync,
                    "git",
                    fake_diff_git(
                        ["src/one.rs", ".github/workflows/x.yml", "fork-feed/latest.json"]
                    ),
                ),
            ):
                fork_sync.verify_changed_paths(SimpleNamespace(source_sha="b" * 40))

    def test_verify_changed_paths_flags_unassigned_source_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            patches = Path(tmp)
            write_patch_package(patches, "one", "src/one.rs")

            with (
                mock.patch.object(fork_sync, "PATCHES_DIR", patches),
                mock.patch.object(
                    fork_sync, "git", fake_diff_git(["src/one.rs", "src/extra.rs"])
                ),
            ):
                with self.assertRaisesRegex(SystemExit, "src/extra.rs"):
                    fork_sync.verify_changed_paths(
                        SimpleNamespace(source_sha="b" * 40)
                    )

    def test_update_frontmatter_updates_only_derived_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            patches = Path(tmp)
            write_patch_package(patches, "one", "src/one.rs")
            document = patches / "one" / "PATCH.md"

            fork_sync.update_frontmatter(document, "b" * 40, "c" * 64)

            content = document.read_text()
            self.assertIn(f"baseline: {'b' * 40}", content)
            self.assertIn(f"patch_sha256: {'c' * 64}", content)
            self.assertIn("summary: Test patch.", content)


if __name__ == "__main__":
    unittest.main()
