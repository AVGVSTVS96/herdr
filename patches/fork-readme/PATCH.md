---
format: patch-md/v0.1
id: fork-readme
summary: Prepend a fork install banner to the top of the upstream README.
baseline: 9a4ce5e13c1d4622ca63c2947d0eaa018ec35715
patch_file: fork-readme.patch
patch_sha256: 2d8e6c7bffe014cb21cf12603ab0cfef1671b190aaa1be47519cc93505e710d4
---

## Intent

Prepend a GitHub note-style banner block at the very top of `README.md`,
before upstream's `# herdr` heading. The banner explains that this
repository is an auto-patched fork, links the `patches/` directory, gives
the one-line `install-fork.sh` install command, and states how updates and
the preview nightly channel work.

The banner text must be preserved verbatim and must remain the first
content in the file. Nothing else in the upstream README may change; if
upstream edits the top of its README, keep their content intact directly
below the banner.

## Verification

`git apply` succeeds against the baseline and GitHub renders the note
block above the upstream heading. Covered by `fork_sync.py validate` and
the sync workflow's scope fence.

## Removal

Remove this patch if the fork stops publishing patched builds or the
banner moves into a fork-owned file outside the synced tree.
