---
format: patch-md/v0.1
id: heal-overflow
summary: Healed changes not yet attributed to a named patch package.
baseline: 2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01
patch_file: heal-overflow.patch
patch_sha256: 32181397ed76b0aa3bfd3862e88956d6529905b912ef45e262092c9bbfe7ca38
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
