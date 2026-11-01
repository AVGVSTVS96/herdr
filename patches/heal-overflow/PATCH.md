---
format: patch-md/v0.1
id: heal-overflow
summary: Healed changes not yet attributed to a named patch package.
baseline: ee5bfb5041bb3e4a49d591c72308aae3c81ecdde
patch_file: heal-overflow.patch
patch_sha256: 40723f913e817bc9bb5c4c69dd8fc3efd5a3801c73e171ed811efe09d3dfa707
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
