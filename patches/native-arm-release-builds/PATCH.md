---
id: native-arm-release-builds
summary: Build Linux ARM64 release artifacts on native GitHub-hosted ARM runners.
baseline: ef4c23f5775bb8cfec05f05d0844226ff959a07a
lastUpdated: 2026-07-23
---

## Intent

Build `aarch64-unknown-linux-musl` release and preview artifacts on
GitHub's native `ubuntu-24.04-arm` runner instead of cross-compiling them
on an x86_64 `ubuntu-latest` runner.

Native ARM builds must retain the same artifact names, Rust target,
release optimization settings, static-binary verification, caches, and
publishing behavior as the existing cross-compiled builds.

Because the runner architecture matches the Rust target, install only
the common Linux build dependencies (`cmake`, `ninja-build`, and
`musl-tools`). Do not install the AArch64 GNU cross toolchain and do not
set an AArch64 cross-linker override.

Keep x86_64 Linux on `ubuntu-latest` and both macOS targets on
`macos-latest`.

## Verification

Validate all modified workflow YAML and run `actionlint`.

Run a release build and confirm that the Linux ARM64 job:

- is assigned to an ARM64 `ubuntu-24.04-arm` runner
- builds `aarch64-unknown-linux-musl` successfully
- produces the unchanged `herdr-linux-aarch64` artifact
- passes the existing static-binary verification

## Removal condition

Remove this patch only when upstream Herdr builds Linux ARM64 release
artifacts natively, or when GitHub retires this runner label and an
equivalent supported native ARM64 runner replaces it.
