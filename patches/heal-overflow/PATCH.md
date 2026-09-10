---
format: patch-md/v0.1
id: heal-overflow
summary: Healed changes not yet attributed to a named patch package.
baseline: 241a1e0fad651f441d97b8373f14ef193b3d9faf
patch_file: heal-overflow.patch
patch_sha256: e00fe5c0c2ebc7bdd494fc63f6acdbffefdf338c3c2bcb6335b0bf45f1a3dae2
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
