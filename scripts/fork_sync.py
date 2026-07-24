#!/usr/bin/env python3
"""Small deterministic helpers for the patched-fork workflow."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCHES_DIR = ROOT / "patches"
CONTROL_PATHS = {
    ".github/workflows/sync-upstream.yml",
    "install-fork.sh",
    "scripts/fork_sync.py",
    "scripts/test_fork_sync.py",
}
CONTROL_PREFIXES = ("patches/", "fork-feed/")


def patch_dirs() -> list[Path]:
    return sorted(path.parent for path in PATCHES_DIR.glob("*/meta.json"))


def load_meta(directory: Path) -> dict:
    return json.loads((directory / "meta.json").read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate() -> list[dict]:
    directories = patch_dirs()
    if not directories:
        raise SystemExit("no patch metadata found")

    metas: list[dict] = []
    claimed_paths: dict[str, str] = {}
    expected_source: tuple[str, str, str, str] | None = None
    for directory in directories:
        meta = load_meta(directory)
        patch_id = meta.get("id")
        if meta.get("schema_version") != 1 or patch_id != directory.name:
            raise SystemExit(f"invalid metadata identity in {directory}")
        if meta.get("track") not in {"stable", "main"}:
            raise SystemExit(f"invalid track in {directory}")
        source_sha = meta.get("source_sha", "")
        if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
            raise SystemExit(f"invalid source_sha in {directory}")
        source = (
            meta["track"],
            meta.get("source_kind", ""),
            source_sha,
            meta.get("source_tag", ""),
        )
        if expected_source is None:
            expected_source = source
        elif source != expected_source:
            raise SystemExit("all patches must describe the same upstream source")

        patch_path = directory / f"{patch_id}.patch"
        intent_path = directory / "PATCH.md"
        if not patch_path.is_file() or not patch_path.read_bytes():
            raise SystemExit(f"missing or empty patch: {patch_path}")
        if not intent_path.is_file():
            raise SystemExit(f"missing intent: {intent_path}")
        if sha256(patch_path) != meta.get("patch_sha256"):
            raise SystemExit(f"patch checksum mismatch: {patch_path}")
        intent = intent_path.read_text()
        if f"baseline: {source_sha}" not in intent:
            raise SystemExit(f"PATCH.md baseline does not match meta.json: {directory}")

        paths = meta.get("paths")
        if not isinstance(paths, list) or not paths:
            raise SystemExit(f"patch paths must be a non-empty list: {directory}")
        for path in paths:
            if not isinstance(path, str) or not path or path.startswith("/"):
                raise SystemExit(f"invalid patch path in {directory}: {path!r}")
            if path in claimed_paths:
                raise SystemExit(
                    f"{path} is claimed by both {claimed_paths[path]} and {patch_id}"
                )
            claimed_paths[path] = patch_id
        metas.append(meta)
    return metas


def git(*args: str, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=text,
    )


def update_frontmatter(path: Path, source_sha: str) -> None:
    content = path.read_text()
    content, baseline_count = re.subn(
        r"(?m)^baseline: .+$", f"baseline: {source_sha}", content, count=1
    )
    content, date_count = re.subn(
        r"(?m)^lastUpdated: .+$",
        f"lastUpdated: {dt.datetime.now(dt.timezone.utc).date().isoformat()}",
        content,
        count=1,
    )
    if baseline_count != 1 or date_count != 1:
        raise SystemExit(f"invalid PATCH.md frontmatter: {path}")
    path.write_text(content)


def refresh(args: argparse.Namespace) -> None:
    metas = validate()
    for old_meta, directory in zip(metas, patch_dirs(), strict=True):
        paths = old_meta["paths"]
        result = git(
            "diff",
            "--binary",
            "--full-index",
            args.source_sha,
            "--",
            *paths,
            text=False,
        )
        patch_path = directory / f"{old_meta['id']}.patch"
        patch_path.write_bytes(result.stdout)
        if not result.stdout:
            raise SystemExit(
                f"{old_meta['id']} became empty; review its removal condition"
            )

        meta = {
            **old_meta,
            "track": args.track,
            "source_kind": args.source_kind,
            "source_sha": args.source_sha,
            "source_tag": args.source_tag,
            "patch_sha256": sha256(patch_path),
        }
        (directory / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
        update_frontmatter(directory / "PATCH.md", args.source_sha)
    validate()


def verify_changed_paths(args: argparse.Namespace) -> None:
    metas = validate()
    claimed = {path for meta in metas for path in meta["paths"]}
    changed = git("diff", "--name-only", args.source_sha).stdout.splitlines()
    unexpected = [
        path
        for path in changed
        if path not in claimed
        and path not in CONTROL_PATHS
        and not path.startswith(CONTROL_PREFIXES)
    ]
    if unexpected:
        raise SystemExit(
            "changed source paths are not assigned to a patch:\n"
            + "\n".join(f"  {path}" for path in unexpected)
        )


def asset_metadata(asset_dir: Path, tag: str, repository: str) -> dict:
    mapping = {
        "linux-x86_64": "herdr-linux-x86_64",
        "linux-aarch64": "herdr-linux-aarch64",
        "macos-x86_64": "herdr-macos-x86_64",
        "macos-aarch64": "herdr-macos-aarch64",
    }
    assets = {}
    for target, name in mapping.items():
        path = asset_dir / name
        if not path.is_file():
            raise SystemExit(f"missing release asset: {path}")
        assets[target] = {
            "url": f"https://github.com/{repository}/releases/download/{tag}/{name}",
            "sha256": sha256(path),
        }
    return assets


def write_manifest(args: argparse.Namespace) -> None:
    output = Path(args.output)
    previous = {}
    if output.is_file():
        previous = json.loads(output.read_text())
    assets = asset_metadata(Path(args.asset_dir), args.tag, args.repository)

    if args.channel == "stable":
        releases = previous.get("releases", {})
        releases[args.version] = {
            "notes": args.notes,
            "protocol": args.protocol,
            "assets": assets,
        }
        manifest = {
            "version": args.version,
            "protocol": args.protocol,
            "notes": args.notes,
            "assets": assets,
            "releases": releases,
        }
    else:
        builds = previous.get("builds", {})
        build = {
            "base_version": args.version,
            "commit": args.source_sha,
            "built_at": args.built_at,
            "protocol": args.protocol,
            "assets": assets,
        }
        builds[args.build_id] = build
        manifest = {
            "channel": "preview",
            "base_version": args.version,
            "build_id": args.build_id,
            "commit": args.source_sha,
            "built_at": args.built_at,
            "protocol": args.protocol,
            "notes": args.notes,
            "assets": assets,
            "builds": builds,
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("validate")

    refresh_parser = commands.add_parser("refresh")
    refresh_parser.add_argument("--track", choices=["stable", "main"], required=True)
    refresh_parser.add_argument("--source-kind", required=True)
    refresh_parser.add_argument("--source-sha", required=True)
    refresh_parser.add_argument("--source-tag", default="")

    changed_parser = commands.add_parser("verify-changed-paths")
    changed_parser.add_argument("--source-sha", required=True)

    manifest = commands.add_parser("write-manifest")
    manifest.add_argument("--channel", choices=["stable", "preview"], required=True)
    manifest.add_argument("--version", required=True)
    manifest.add_argument("--protocol", type=int, required=True)
    manifest.add_argument("--tag", required=True)
    manifest.add_argument("--repository", required=True)
    manifest.add_argument("--asset-dir", required=True)
    manifest.add_argument("--output", required=True)
    manifest.add_argument("--notes", required=True)
    manifest.add_argument("--source-sha", default="")
    manifest.add_argument("--build-id", default="")
    manifest.add_argument("--built-at", default="")
    return root


def main() -> None:
    args = parser().parse_args()
    if args.command == "validate":
        validate()
    elif args.command == "refresh":
        refresh(args)
    elif args.command == "verify-changed-paths":
        verify_changed_paths(args)
    elif args.command == "write-manifest":
        write_manifest(args)


if __name__ == "__main__":
    main()
