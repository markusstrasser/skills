#!/bin/bash
# codex-tier-shim pins headless runs to Standard and leaves everything else alone; codex-tier-audit names escapes.
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd); T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
printf '#!/bin/sh\nprintf "%%s\\n" "$@"\n' > "$T/real"; chmod +x "$T/real"
fails=0
check() { [ "$2" = "$3" ] || { echo "FAIL: $1: expected [$2] got [$3]"; fails=$((fails + 1)); }; }
shim() { CODEX_REAL="$T/real" "$ROOT/bin/codex-tier-shim" "$@" | tr '\n' ' ' | sed 's/ $//'; }
pin='-c service_tier="default"'
check "exec is pinned" "$pin exec hello" "$(shim exec hello)"
check "the alias e is pinned" "$pin e hello" "$(shim e hello)"
check "root options before exec" "$pin -m gpt-6.1-sol exec hello" "$(shim -m gpt-6.1-sol exec hello)"
check "root -c before exec" "$pin -c a=1 exec hello" "$(shim -c a=1 exec hello)"
check "a named tier comes later and wins" "$pin exec -c service_tier=\"ultrafast\" hello" "$(shim exec -c 'service_tier="ultrafast"' hello)"
check "the client passes through" "" "$(shim)"
check "resume passes through" "resume --last" "$(shim resume --last)"
check "exec as an option's value is not exec" "-m exec" "$(shim -m exec)"
check "a prompt naming exec is not exec" "resume exec" "$(shim resume exec)"
rc=0; CODEX_REAL="$T/none" "$ROOT/bin/codex-tier-shim" exec x >/dev/null 2>&1 || rc=$?
check "a missing binary fails loud" "127" "$rc"
S="$T/sessions/2026/11/05"; mkdir -p "$S"
row() { printf '{"type":"session_meta","payload":{"originator":"%s","cwd":"/w/%s"}}\n{"type":"event_msg","payload":{"type":"thread_settings_applied","thread_settings":{"service_tier":"%s"}}}\n' "$1" "$2" "$3" > "$S/rollout-$2.jsonl"; }
row codex_exec good default; row "Codex Desktop" mine ultrafast
out=$(LANE_CODEX_SESSIONS="$T/sessions" "$ROOT/bin/codex-tier-audit"); rc=$?
check "the audit passes Standard and ignores Desktop" "0 1" "$rc $(printf '%s' "$out" | grep -c '1 headless runs')"
row codex_exec bad ultrafast
out=$(LANE_CODEX_SESSIONS="$T/sessions" "$ROOT/bin/codex-tier-audit"); rc=$?
check "the audit fails on an Ultrafast headless run" "1 1" "$rc $(printf '%s' "$out" | grep -c 'ultrafast bad')"
[ "$fails" = 0 ] && echo "test_codex_tier_shim: ok"
exit "$fails"
