---
format: patch-md/v0.1
id: heal-overflow
summary: Healed changes not yet attributed to a named patch package.
baseline: dbc398f580d1da6c336c6837a60b7e0710501d6d
patch_file: heal-overflow.patch
patch_sha256: 95f57fb8ca7bc42f73ced5136784ce5036f10c157207ec79bf3b305468eb9f72
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
