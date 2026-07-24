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

    def test_preview_manifest_preserves_previous_builds(self):
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
            output.write_text(json.dumps({"builds": {"old": {"commit": "old"}}}))
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
            self.assertIn("old", manifest["builds"])
            self.assertEqual(
                manifest["builds"]["2026-07-23-abcdef"]["commit"], "b" * 40
            )

    def test_validate_rejects_duplicate_claimed_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            patches = Path(tmp)
            for patch_id in ("one", "two"):
                directory = patches / patch_id
                directory.mkdir()
                patch = directory / f"{patch_id}.patch"
                patch.write_text("diff")
                (directory / "PATCH.md").write_text(
                    "---\nbaseline: " + "a" * 40 + "\nlastUpdated: 2026-07-23\n---\n"
                )
                (directory / "meta.json").write_text(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "id": patch_id,
                            "track": "stable",
                            "source_kind": "release",
                            "source_sha": "a" * 40,
                            "source_tag": "v1.0.0",
                            "patch_sha256": fork_sync.sha256(patch),
                            "paths": ["same.rs"],
                        }
                    )
                )

            with mock.patch.object(fork_sync, "PATCHES_DIR", patches):
                with self.assertRaisesRegex(SystemExit, "claimed by both"):
                    fork_sync.validate()


if __name__ == "__main__":
    unittest.main()
