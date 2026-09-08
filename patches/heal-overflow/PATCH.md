---
format: patch-md/v0.1
id: heal-overflow
summary: Healed changes not yet attributed to a named patch package.
baseline: b99002ac99b09e00b4ca692436cb15a6b0d676f1
patch_file: heal-overflow.patch
patch_sha256: 30ad5c1eb9f408074774ebc95b52f40f4edf8cbac5882b54807691dfedcc62fe
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
