#!/usr/bin/env bash
# pretool-timeout-modal-guard.sh — Block `timeout N <Modal/volume-crawl>`.
#
# Wrapping a Modal-touching command in `timeout N` SIGTERMs it at the deadline
# (exit 143) MID-CRAWL — killing a dispatch/remediation/volume-ls partway and
# wasting the run + the agent's time. The right pattern is run_in_background=true
# (you get a completion notification) or the command's own --timeout flag.
#
# Evidence: 2026-06-24 genomics session hit this 4x in one session
# (`timeout 180 just dispatch`, `timeout 200 just complete-sample`,
#  `timeout 240 just sample-remediation`, `timeout 60 modal volume ls`) —
# every one SIGTERM'd a Modal crawl. Generalizes the memory
# `feedback_no_subprocess_timeout_modal` (which covered only `modal run --detach`).
#
# Fail-open: only an intentional exit 2 (block) propagates; a python crash or any
# other exit → exit 0, so a hook bug never blocks real work.
#
# Body is a quoted heredoc (NOT `python3 -c '...'`): regexes here need apostrophes,
# and a prose apostrophe inside -c closes the shell quote (posttool-hook-syntax-guard
# caught exactly that on 2026-07-11). Input rides an env var since the heredoc owns stdin.

HOOK_INPUT=$(cat) python3 <<'PYEOF'
import os, sys, json, re

try:
    data = json.loads(os.environ.get("HOOK_INPUT", ""))
except Exception:
    sys.exit(0)

if data.get("tool_name") != "Bash":
    sys.exit(0)

cmd = data.get("tool_input", {}).get("command", "") or ""
if not cmd:
    sys.exit(0)

# Only care when the command is wrapped in `timeout <N>` (GNU/coreutils form,
# optional -k/-s flags). Bare `timeout` without a leading duration is rare; the
# duration may be 30, 30s, 1m, etc.
#
# COMMAND-POSITION ANCHOR (2026-07-11): heredoc/quoted PROSE containing "timeout 5h"
# false-positived this guard 2x in one launch (arc-agi fork trains — the blocked
# command's only wrapper-shaped text was inside a `cat << EOF` prereg amendment).
# Strip heredoc bodies, then require `timeout` at a command boundary (start / ;&|( /
# $( / backtick / after nohup|sudo|env-assignments) — a wrapper can only occur there.
scan = re.sub(r"<<-?\s*'?([A-Za-z_]\w*)'?.*?\n\1\s*$", " ", cmd, flags=re.S | re.M)
_WRAP = (
    r"(?:^|[;&|(]\s*|\$\(\s*|`\s*)"
    r"(?:nohup\s+|sudo\s+|[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*"
    r"timeout\s+(?:-[ksv]\S*\s+)*\d+(?:\.\d+)?[smhd]?\s"
)
if not re.search(_WRAP, scan, flags=re.M):
    sys.exit(0)
cmd = scan  # CRAWL check below must also ignore heredoc prose

# EXEMPTION: log STREAMS (`modal app logs`, `modal container logs`) are the one modal
# case where `timeout` is CORRECT, not destructive — they follow forever and have no
# partial crawl state to waste, so SIGTERM at the deadline just ends a bounded tail. The
# streaming-cli-guard even REQUIRES a timeout on them; blocking it here left log
# inspection with no legal form (both guards firing). Exempt and fail open.
if re.search(r"\bmodal\s+(?:app|container)\s+logs\b", cmd):
    sys.exit(0)

# Modal/volume-crawl signatures: the live-Modal `just` recipes + raw modal CLI
# crawls + the orchestrator subcommands. These do volume.reload / 258-stage
# ledger crawls / detached launches that a timeout truncates destructively.
CRAWL = re.compile(
    r"\bmodal\s+(?:volume|run|app|container)\b"
    r"|\bjust\s+(?:dispatch|sample-remediation|sample-state|sample-readiness"
    r"|complete-sample|pipeline-run|pipeline-rerun|pipeline-rerun-vcf|census"
    r"|volume-status|stage-status|probe|download-results)\b"
    r"|pipeline_orchestrator\.py\s+(?:dispatch|rerun|run|resume|recover|reconcile|reconcile-runs|backfill|sync-cass)\b"
    r"|complete_sample\.py"
    r"|\bmodal_sync_results\.py\b",
)
if not CRAWL.search(cmd):
    sys.exit(0)

msg = (
    "BLOCKED: `timeout N` wraps a Modal/volume-crawl command. At the deadline it\n"
    "sends SIGTERM (exit 143) and kills the crawl MID-RUN — wasting the dispatch/\n"
    "remediation/volume-ls and any partial state. (genomics 2026-06-24: this footgun\n"
    "fired 4x in one session.)\n"
    "Fix: DROP `timeout N` and either\n"
    "  - run_in_background=true  (tracked; you get a completion notification), or\n"
    "  - use the commands OWN bound (`just dispatch ... --detach`, llmx `--timeout`),\n"
    "    or `modal volume ls` (already fast) without the wrapper.\n"
    "Never SIGTERM a Modal crawl to bound it."
)
print(msg, file=sys.stderr)
sys.exit(2)
PYEOF
rc=$?
if [ "$rc" = "2" ]; then exit 2; fi
exit 0
