An install of this fork updates from this fork, never from upstream. This fork
publishes its own GitHub Releases of herdr, under the same tag as the upstream
release each is built on, with a `latest.json` update manifest in upstream's
format next to the binaries. Left alone, herdr's updater reads
https://herdr.dev/latest.json and would swap the fork's binary for upstream's
on the next update, dropping every patch.

So wherever herdr fetches an update manifest (today the updater behind
`herdr update` and its background checks, and the remote-session code that
seeds a matching binary on an SSH host), the stable manifest comes from
https://github.com/AVGVSTVS96/herdr/releases/latest/download/latest.json, and
the preview one from the same place's `preview.json`. The fork follows
upstream's stable releases and publishes no previews, so a fork install set to
the preview channel finds no update instead of installing upstream's preview.
Any manifest fetch upstream adds later points at the fork the same way.

The release workflow itself lives in `.github/workflows/release.yml`, which
autofork treats as the fork's own file; this patch only covers the app's
source.
