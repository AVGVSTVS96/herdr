---
format: patch-md/v0.1
id: fork-update-feed
summary: Compile published fork binaries against fork-owned stable and preview update manifests.
baseline: 73d92004f50d3f5fafe64e0f9b7fddbcf4d99965
patch_file: fork-update-feed.patch
patch_sha256: a1796ccaa4b7836748064d7d4ddaa93951d9289d68da80a774f8639c2ca0bb47
---

## Intent

Allow release builds to override Herdr's stable and preview manifest URLs
at compile time without changing normal upstream defaults.

The build-time variables are:

- `HERDR_STABLE_UPDATE_MANIFEST_URL`
- `HERDR_PREVIEW_UPDATE_MANIFEST_URL`

Unset or blank variables must continue to use `https://herdr.dev/latest.json`
and `https://herdr.dev/preview.json`. Published fork binaries set both
variables to manifests owned by this fork, so native background checks,
`herdr channel set`, and `herdr update --handoff` never replace the fork
with an upstream binary.

Every code path that fetches an update manifest must resolve its URL
through this single override, not a private constant. Today that covers
the updater and remote-session binary seeding; extend the same routing
to any manifest fetch upstream adds later.

Register both variables with Cargo's build-script rerun tracking.

## Verification

Run `just check`. Release builds must set both URLs explicitly.

## Removal

Remove this patch only if upstream Herdr gains a supported persistent
custom update-feed mechanism that provides the same stable and preview
behavior without requiring user shell environment variables.
