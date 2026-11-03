An install of this fork updates from this fork, never from upstream. The fork publishes its own GitHub Releases of herdr, under the same tag as the upstream release each is built on, with a `latest.json` update manifest in herdr.dev's format next to the binaries. Left alone, herdr reads https://herdr.dev/latest.json, and its background checks, `herdr channel set` and `herdr update --handoff` would swap the fork's binary for upstream's on the next update, dropping every patch.

So every place herdr fetches an update manifest reads this fork's instead: the stable one from https://github.com/AVGVSTVS96/herdr/releases/latest/download/latest.json, and the preview one from the same place's `preview.json`. They resolve through one definition, not a private copy in each caller. Today that's the updater behind `herdr update` and its background checks, and the remote-session code that seeds a matching binary on an SSH host; any manifest fetch upstream adds later points at the fork the same way. Upstream's Unix installer, `distribution/install.sh`, reads the fork's `latest.json` too, so the one-line install in the README installs this fork's build, checked against its sha256. The fork builds no Windows binary, so the Windows installer stays upstream's.

The fork follows upstream's stable releases and publishes no previews, so a fork install set to the preview channel finds no update instead of installing upstream's preview.

Earlier this fork compiled the two URLs in from build-time variables (`HERDR_STABLE_UPDATE_MANIFEST_URL`, `HERDR_PREVIEW_UPDATE_MANIFEST_URL`) that only its release builds set, keeping herdr.dev as the default. Pointing the source itself at the fork is smaller, and an install built from this fork's source also stays on the fork.

The release workflow lives in `.github/workflows/release.yml`, the fork's own file; this patch only covers the app's source and its installer.

Once herdr itself lets an install follow another release feed for good, for stable and preview, without shell environment variables, this patch is done.
