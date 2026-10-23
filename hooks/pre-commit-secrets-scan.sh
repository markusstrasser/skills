#!/usr/bin/env bash
# pre-commit-secrets-scan.sh — block a commit whose staged changes add a credential.
#
# WHY: the pretool-secret-* hooks guard what an agent reads and prints, but nothing checked
# what a commit adds. agent-infra is public, and a PharmVar key (2026-04) and an Anthropic
# key (2026-07) reached its history; both needed history rewrites (2026-10-24 gitleaks scan).
# A git-native hook covers every commit path, the auto-[wip] checkpoint included.
#
# Rules: gitleaks.toml beside this script (defaults minus research-data false positives).
# Staged paths with filter=git-crypt are skipped: the object store holds only ciphertext.
# A known false positive goes in <repo-root>/.gitleaksignore by fingerprint.
#
# Exit: 0 pass · 1 block. Missing gitleaks or a gitleaks error prints [DEGRADED] and passes.
# Bypass: GIT_ALLOW_GUARD_BYPASS=1.

set -uo pipefail
[ "${GIT_ALLOW_GUARD_BYPASS:-0}" = "1" ] && exit 0

if ! command -v gitleaks >/dev/null 2>&1; then
    echo "[DEGRADED] pre-commit-secrets-scan: gitleaks not installed; staged changes not scanned (brew install gitleaks)" >&2
    exit 0
fi

_src="${BASH_SOURCE[0]}"
while [ -L "$_src" ]; do
    _ld="$(cd -P "$(dirname "$_src")" && pwd)"
    _src="$(readlink "$_src")"
    case "$_src" in /*) ;; *) _src="$_ld/$_src" ;; esac
done
HOOKS_DIR="$(cd -P "$(dirname "$_src")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel)" || exit 0

cfg="$(mktemp "${TMPDIR:-/tmp}/gitleaks-precommit.XXXXXX")"
trap 'rm -f "$cfg"' EXIT
{
    printf '[extend]\npath = "%s"\n' "$HOOKS_DIR/gitleaks.toml"
    # `git check-attr -z` emits path NUL attr NUL value NUL per staged path.
    crypt=()
    while IFS= read -r -d '' path && IFS= read -r -d '' _attr && IFS= read -r -d '' value; do
        [ "$value" = "git-crypt" ] && crypt+=("$path")
    done < <(git -C "$REPO_ROOT" diff --cached --name-only -z --diff-filter=ACMR \
        | git -C "$REPO_ROOT" check-attr -z --stdin filter)
    if [ "${#crypt[@]}" -gt 0 ]; then
        printf "[[allowlists]]\ndescription = \"git-crypt ciphertext\"\npaths = [\n"
        for path in "${crypt[@]}"; do
            printf "  '''^%s$''',\n" "$(printf '%s' "$path" | sed 's/[][\.^$*+?(){}|]/\\&/g')"
        done
        printf "]\n"
    fi
} >"$cfg"

gitleaks git --pre-commit --staged --redact --no-banner --log-level warn \
    --exit-code 3 -c "$cfg" "$REPO_ROOT"
rc=$?
case $rc in
    0) exit 0 ;;
    3)
        echo "BLOCKED: gitleaks found a credential in the staged changes (values redacted above)." >&2
        echo "  Move it to the keychain store (~/dotfiles/scripts/secret) and restage." >&2
        echo "  False positive: add its Fingerprint line to $REPO_ROOT/.gitleaksignore." >&2
        exit 1
        ;;
    *)
        echo "[DEGRADED] pre-commit-secrets-scan: gitleaks exited $rc; staged changes not scanned" >&2
        exit 0
        ;;
esac
