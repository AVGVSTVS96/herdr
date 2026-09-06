---
format: patch-md/v0.1
id: heal-overflow
summary: Healed changes not yet attributed to a named patch package.
baseline: e366a05f03b6e37549c7a1744c3551553017c541
patch_file: heal-overflow.patch
patch_sha256: ab971778d0145b15246c6ed401cd63714c69ea484882e7013616cd0a96d6f9f2
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
