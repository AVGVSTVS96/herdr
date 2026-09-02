---
format: patch-md/v0.1
id: heal-overflow
summary: Healed changes not yet attributed to a named patch package.
baseline: 8633a398e653eee47b375c963996c78a8a14aa48
patch_file: heal-overflow.patch
patch_sha256: 01b4fe93b1a7032fb653c21a06fd07b65b272b729e12a2ba56360dc9a944c526
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
