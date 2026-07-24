#!/usr/bin/env python3
"""Small deterministic helpers for the patched-fork workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import NamedTuple


ROOT = Path(__file__).resolve().parents[1]
PATCHES_DIR = ROOT / "patches"
CONTROL_PATHS = {
    ".github/workflows/sync-upstream.yml",
    "install-fork.sh",
    "scripts/fork_sync.py",
    "scripts/test_fork_sync.py",
}
CONTROL_PREFIXES = ("patches/", "fork-feed/")
PATCH_FORMAT = "patch-md/v0.1"


class PatchSpec(NamedTuple):
    directory: Path
    patch_id: str
    baseline: str
    patch_path: Path
    patch_sha256: str
    paths: tuple[str, ...]


def patch_docs() -> list[Path]:
    return sorted(PATCHES_DIR.glob("*/PATCH.md"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text().splitlines()
    if not lines or lines[0] != "---":
        raise SystemExit(f"missing PATCH.md frontmatter: {path}")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise SystemExit(f"unterminated PATCH.md frontmatter: {path}") from None

    values: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        if not separator or not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise SystemExit(f"invalid PATCH.md frontmatter line in {path}: {line!r}")
        if key in values:
            raise SystemExit(f"duplicate PATCH.md frontmatter key in {path}: {key}")
        values[key] = value.strip()
    return values


def numstat_paths(path: Path, *, reverse: bool = False) -> list[str]:
    command = ["git", "apply"]
    if reverse:
        command.append("--reverse")
    command.extend(("--numstat", "-z", str(path)))
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
    )
    if result.returncode:
        detail = result.stderr.decode(errors="replace").strip()
        raise SystemExit(f"invalid patch {path}: {detail}")
    fields = result.stdout.split(b"\0")
    paths: list[str] = []
    index = 0
    while index < len(fields) and fields[index]:
        record = fields[index]
        parts = record.split(b"\t", 2)
        if len(parts) != 3:
            raise SystemExit(f"cannot read paths from patch: {path}")
        if parts[2]:
            raw_paths = (parts[2],)
            index += 1
        else:
            if index + 2 >= len(fields):
                raise SystemExit(f"cannot read rename paths from patch: {path}")
            raw_paths = (fields[index + 1], fields[index + 2])
            index += 3
        for raw_path in raw_paths:
            decoded = os.fsdecode(raw_path)
            candidate = Path(decoded)
            if not decoded or candidate.is_absolute() or ".." in candidate.parts:
                raise SystemExit(f"unsafe path in {path}: {decoded!r}")
            paths.append(decoded)
    return paths


def patch_paths(path: Path) -> tuple[str, ...]:
    paths = numstat_paths(path)
    paths.extend(numstat_paths(path, reverse=True))
    return tuple(dict.fromkeys(paths))


def validate_body(path: Path) -> None:
    headings = re.findall(r"(?m)^## ([^\n]+)$", path.read_text())
    for required in ("Intent", "Verification", "Removal"):
        if headings.count(required) != 1:
            raise SystemExit(f"PATCH.md must contain one ## {required} section: {path}")
    if "Patch" in headings:
        raise SystemExit(f"external PATCH.md must not contain an inline patch: {path}")


def load_patch(path: Path) -> PatchSpec:
    directory = path.parent
    frontmatter = parse_frontmatter(path)
    required = {
        "format",
        "id",
        "summary",
        "baseline",
        "patch_file",
        "patch_sha256",
    }
    missing = sorted(required - frontmatter.keys())
    if missing:
        raise SystemExit(f"missing PATCH.md fields in {path}: {', '.join(missing)}")
    if frontmatter["format"] != PATCH_FORMAT:
        raise SystemExit(f"unsupported PATCH.md format in {path}")
    patch_id = frontmatter["id"]
    if (
        not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", patch_id)
        or patch_id != directory.name
    ):
        raise SystemExit(f"PATCH.md id does not match directory: {path}")
    if not frontmatter["summary"]:
        raise SystemExit(f"PATCH.md summary must not be empty: {path}")
    baseline = frontmatter["baseline"]
    if not re.fullmatch(r"[0-9a-f]{40}", baseline):
        raise SystemExit(f"invalid PATCH.md baseline in {path}")

    patch_file = frontmatter["patch_file"]
    if Path(patch_file).name != patch_file or not patch_file.endswith(".patch"):
        raise SystemExit(f"invalid PATCH.md patch_file in {path}")
    patch_path = directory / patch_file
    if (
        patch_path.is_symlink()
        or not patch_path.is_file()
        or not patch_path.read_bytes()
    ):
        raise SystemExit(f"missing or empty patch: {patch_path}")
    unexpected = sorted(
        member.name
        for member in directory.iterdir()
        if member not in {path, patch_path}
    )
    if unexpected:
        raise SystemExit(
            f"unexpected files in patch package {directory}: {', '.join(unexpected)}"
        )
    expected_hash = frontmatter["patch_sha256"]
    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise SystemExit(f"invalid PATCH.md patch_sha256 in {path}")
    if sha256(patch_path) != expected_hash:
        raise SystemExit(f"patch checksum mismatch: {patch_path}")
    validate_body(path)
    paths = patch_paths(patch_path)
    if not paths:
        raise SystemExit(f"patch does not change any paths: {patch_path}")
    return PatchSpec(
        directory=directory,
        patch_id=patch_id,
        baseline=baseline,
        patch_path=patch_path,
        patch_sha256=expected_hash,
        paths=paths,
    )


def validate() -> list[PatchSpec]:
    documents = patch_docs()
    if not documents:
        raise SystemExit("no PATCH.md files found")

    patches: list[PatchSpec] = []
    claimed_paths: dict[str, str] = {}
    expected_baseline: str | None = None
    for document in documents:
        patch = load_patch(document)
        if expected_baseline is None:
            expected_baseline = patch.baseline
        elif patch.baseline != expected_baseline:
            raise SystemExit("all patches must use the same baseline")
        for changed_path in patch.paths:
            if changed_path in claimed_paths:
                raise SystemExit(
                    f"{changed_path} is changed by both "
                    f"{claimed_paths[changed_path]} and {patch.patch_id}"
                )
            claimed_paths[changed_path] = patch.patch_id
        patches.append(patch)
    return patches


def git(*args: str, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=text,
    )


def update_frontmatter(path: Path, source_sha: str, patch_hash: str) -> None:
    content = path.read_text()
    content, baseline_count = re.subn(
        r"(?m)^baseline: .+$", f"baseline: {source_sha}", content, count=1
    )
    content, hash_count = re.subn(
        r"(?m)^patch_sha256: .+$",
        f"patch_sha256: {patch_hash}",
        content,
        count=1,
    )
    if baseline_count != 1 or hash_count != 1:
        raise SystemExit(f"invalid PATCH.md frontmatter: {path}")
    path.write_text(content)


def refresh(args: argparse.Namespace) -> None:
    patches = validate()
    for patch in patches:
        result = git(
            "diff",
            "--binary",
            "--full-index",
            args.source_sha,
            "--",
            *patch.paths,
            text=False,
        )
        patch.patch_path.write_bytes(result.stdout)
        if not result.stdout:
            raise SystemExit(
                f"{patch.patch_id} became empty; review its removal condition"
            )
        update_frontmatter(
            patch.directory / "PATCH.md",
            args.source_sha,
            sha256(patch.patch_path),
        )
    validate()


def verify_changed_paths(args: argparse.Namespace) -> None:
    patches = validate()
    claimed = {path for patch in patches for path in patch.paths}
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
    commands.add_parser("baseline")
    commands.add_parser("list-patches")

    refresh_parser = commands.add_parser("refresh")
    refresh_parser.add_argument("--source-sha", required=True)

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
    elif args.command == "baseline":
        print(validate()[0].baseline)
    elif args.command == "list-patches":
        for patch in validate():
            print(patch.patch_path.relative_to(ROOT))
    elif args.command == "refresh":
        refresh(args)
    elif args.command == "verify-changed-paths":
        verify_changed_paths(args)
    elif args.command == "write-manifest":
        write_manifest(args)


if __name__ == "__main__":
    main()
