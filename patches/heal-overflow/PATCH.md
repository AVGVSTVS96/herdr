---
format: patch-md/v0.1
id: heal-overflow
summary: Healed changes not yet attributed to a named patch package.
baseline: 9a2a7af5402f2bc67ab24c8b4c14c6dd20a43bb2
patch_file: heal-overflow.patch
patch_sha256: 51cb7b9b05c321a32daa24ba8162b2089a7cde6175a24bf9ab1be7a59f5a45a5
---

## Intent

Preserve heal output that no named patch package claims, so the next
deterministic sync reproduces the full verified tree unchanged.

## Verification

`git apply` succeeds against the baseline and the synced tree passes
`just check`.

## Removal

Reassign these hunks to the named packages whose intents they
implement; refresh deletes this package automatically once no
unassigned changes remain.
