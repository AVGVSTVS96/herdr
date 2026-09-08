---
format: patch-md/v0.1
id: fork-update-feed
summary: Compile published fork binaries against fork-owned stable and preview update manifests.
baseline: b99002ac99b09e00b4ca692436cb15a6b0d676f1
patch_file: fork-update-feed.patch
patch_sha256: d2c795c9995e0cc8d7680adc1b33e6cf8054d69daa546f57a7581b8543a9f079
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
