#!/bin/sh
set -eu

BIN="herdr"
REPOSITORY="${HERDR_FORK_REPOSITORY:-AVGVSTVS96/herdr}"
MANIFEST_URL="${HERDR_MANIFEST_URL:-https://raw.githubusercontent.com/${REPOSITORY}/main/fork-feed/latest.json}"
INSTALL_DIR="${HERDR_INSTALL_DIR:-$HOME/.local/bin}"

log() { printf '  \033[32m>\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1" >&2; }
err() {
    printf '  \033[31m✗\033[0m %s\n' "$1" >&2
    exit 1
}

need() {
    command -v "$1" >/dev/null 2>&1 || err "requires '$1'"
}

json_scalar() {
    key="$1"
    printf '%s\n' "$MANIFEST" | awk -v key="$key" '
        index($0, "\"" key "\"") {
            line = $0
            sub("^.*\\\"" key "\\\"[[:space:]]*:[[:space:]]*", "", line)
            if (substr(line, 1, 1) == "\"") {
                sub(/^"/, "", line)
                sub(/".*$/, "", line)
            } else {
                sub(/,.*/, "", line)
                gsub(/[[:space:]]/, "", line)
            }
            print line
            exit
        }
    '
}

asset_field() {
    target="$1"
    field="$2"
    printf '%s\n' "$MANIFEST" | awk -F '"' -v target="$target" -v field="$field" '
        index($0, "\"" target "\"") { in_target = 1; next }
        in_target && index($0, "\"" field "\"") {
            for (i = 1; i <= NF; i++) {
                if ($i == field) {
                    print $(i + 2)
                    exit
                }
            }
        }
        in_target && /^[[:space:]]*}/ { exit }
    '
}

checksum_file() {
    path="$1"
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$path" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$path" | awk '{print $1}'
    else
        err "requires sha256sum or shasum to verify the download"
    fi
}

main() {
    if [ "${HERDR_ENV:-}" = "1" ]; then
        err "detach from Herdr and run this installer from an outside terminal"
    fi

    printf '\n      ,ww\n     wWWWWWWW_)  patched herdr installer\n     `WWWWWW'\''    %s\n      II  II\n\n' "$REPOSITORY"

    case "$(uname -s)" in
        Linux) os="linux" ;;
        Darwin) os="macos" ;;
        *) err "unsupported operating system: $(uname -s)" ;;
    esac
    case "$(uname -m)" in
        x86_64 | amd64) arch="x86_64" ;;
        aarch64 | arm64) arch="aarch64" ;;
        *) err "unsupported architecture: $(uname -m)" ;;
    esac
    target="${os}-${arch}"

    need curl
    need awk
    log "fetching the patched stable manifest"
    MANIFEST="$(curl -fsSL --retry 3 --connect-timeout 10 --max-time 20 "$MANIFEST_URL")" ||
        err "cannot fetch $MANIFEST_URL"

    version="$(json_scalar version)"
    protocol="$(json_scalar protocol)"
    url="$(asset_field "$target" url)"
    expected_sha="$(asset_field "$target" sha256)"
    [ -n "$version" ] || err "manifest is missing version"
    [ -n "$protocol" ] || err "manifest is missing protocol"
    [ -n "$url" ] || err "manifest has no asset for $target"
    [ -n "$expected_sha" ] || err "manifest has no checksum for $target"

    running_sessions=""
    old_bin="$(command -v "$BIN" 2>/dev/null || true)"
    if [ -n "$old_bin" ]; then
        running_sessions="$("$old_bin" session list 2>/dev/null |
            awk 'NR > 1 && $2 == "running" { print $1 }' || true)"
    fi

    mkdir -p "$INSTALL_DIR"
    tmp="$(mktemp "${INSTALL_DIR}/.herdr-install.XXXXXX")"
    trap 'rm -f "$tmp"' EXIT HUP INT TERM

    log "downloading patched Herdr v${version} for ${target}"
    curl -fsSL --retry 3 --connect-timeout 10 --max-time 120 "$url" -o "$tmp" ||
        err "download failed"
    actual_sha="$(checksum_file "$tmp")"
    [ "$actual_sha" = "$expected_sha" ] ||
        err "checksum mismatch: expected $expected_sha, got $actual_sha"
    chmod +x "$tmp"
    mv -f "$tmp" "${INSTALL_DIR}/${BIN}"
    trap - EXIT HUP INT TERM

    installed="${INSTALL_DIR}/${BIN}"
    log "installed ${installed}"
    "$installed" channel set stable >/dev/null ||
        err "installed the binary, but could not select the fork stable channel"

    if [ -n "$running_sessions" ]; then
        for session in $running_sessions; do
            log "live-handing off session ${session}"
            if ! "$installed" --session "$session" server live-handoff \
                --import-exe "$installed" \
                --expected-protocol "$protocol" \
                --expected-version "$version"; then
                warn "session ${session} kept its old server; retry the installer or restart that session"
            fi
        done
    fi

    case ":${PATH}:" in
        *":${INSTALL_DIR}:"*) ;;
        *) warn "${INSTALL_DIR} is not on PATH; add: export PATH=\"${INSTALL_DIR}:\$PATH\"" ;;
    esac

    log "ready: $("$installed" --version)"
    printf '\n  Future stable updates:\n\n    herdr update --handoff\n\n'
}

if [ "${HERDR_INSTALLER_SOURCE_ONLY:-0}" != "1" ]; then
    main "$@"
fi
