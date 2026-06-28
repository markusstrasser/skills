#!/usr/bin/env bash
# pretool-f16-midwrite-crawl-guard.sh — Block a full-DAG Modal/volume crawl while
# ANY ephemeral Modal stage-app is live (writing). (genomics F16)
#
# F16: a per-stage VolumeListFiles burst — `modal_sync_results.py … --all`, a
# full-DAG `just sample-remediation/sample-state/sample-readiness` (no --target),
# or a recursive `modal volume ls` over a results root — competes with concurrent
# stage WRITERS for the workspace-wide list quota and THROTTLE-HANGS: there is no
# explicit backoff line, the crawl just silently stops advancing.
# PROVEN: a summary-only pull froze 33 min (genomics 2026-06-28, syn3sr) and a
# full-DAG drive hung 7 h previously. The list quota is WORKSPACE-wide, not
# per-sample, so ANY live ephemeral app is contention — the guard does not need
# to attribute apps to a sample.
#
# Block-with-override: confirmed ≥1 live ephemeral app + a crawl signature → exit 2.
# Override when you KNOW 0 stage-apps are writing (e.g. the drive has fully drained,
# or the live apps belong to a different volume): prefix GENOMICS_F16_ACK=1.
# Fail-open: any error / ambiguity / 0 live apps → exit 0. A hook bug never blocks
# real work; only an intentional exit 2 propagates.
#
# Evidence: docs/ops/2026-06-28-orchestrator-restart-credit-wedge.md (sibling F16
# notes), steward-proposals/2026-06-28-f16-midwrite-volume-crawl-guard.md.

INPUT=$(cat)

printf '%s' "$INPUT" | python3 -c '
import sys, json, re, os, subprocess

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if data.get("tool_name") != "Bash":
    sys.exit(0)
cmd = data.get("tool_input", {}).get("command", "") or ""
if not cmd:
    sys.exit(0)

# Operator override — they assert 0 writers. Accept inline (VAR=1 cmd) or exported.
if os.environ.get("GENOMICS_F16_ACK") or re.search(r"\bGENOMICS_F16_ACK=1\b", cmd):
    sys.exit(0)

# Full-DAG volume-crawl signatures (the VolumeListFiles-burst commands). Scoped
# crawls (--target/--stage, a single non-recursive ls of one stage dir) are cheap
# and excluded — they list one directory, not the whole DAG.
full_dag_pull = (
    re.search(r"modal_sync_results\.py\s+(?:pull|freshness)\b", cmd)
    and re.search(r"--all\b", cmd)
    and not re.search(r"--stage\b", cmd)
)
full_dag_remediation = (
    re.search(r"\bjust\s+(?:sample-remediation|sample-state|sample-readiness)\b", cmd)
    and not re.search(r"--target\b|--stage\b", cmd)
)
recursive_volume_ls = (
    re.search(r"\bmodal\s+volume\s+ls\b.*(?:\s-R\b|--recursive\b)", cmd)
    or re.search(r"\bmodal\s+volume\s+ls\b[^|;&]*samples/\S+/results/?\s*$", cmd)
)
if not (full_dag_pull or full_dag_remediation or recursive_volume_ls):
    sys.exit(0)

# Is ANY ephemeral stage-app live? Fast metadata call; fail-open on any error so a
# Modal auth flake / network blip never blocks legitimate work.
try:
    out = subprocess.run(
        ["modal", "app", "list"], capture_output=True, text=True, timeout=20
    ).stdout
except Exception:
    sys.exit(0)  # cannot confirm liveness -> fail open
# "ephemeral" = a live detached stage run; "deployed" services and "stopped" apps
# are not writers and are excluded.
live = [ln for ln in out.splitlines() if re.search(r"ephemeral", ln, re.I)]
if not live:
    sys.exit(0)  # 0 writers -> safe to crawl

sys.stderr.write(
    "BLOCKED (F16): a full-DAG Modal/volume crawl while {n} ephemeral stage-app(s) are LIVE.\n"
    "Per-stage VolumeListFiles bursts compete with the writers for the workspace list quota\n"
    "and THROTTLE-HANG (no backoff line — the crawl silently stops advancing). PROVEN to\n"
    "freeze a pull 33 min (syn3sr 2026-06-28) and hang a drive 7 h.\n"
    "Fix: WAIT for the drive to drain (0 live stage-apps), THEN crawl; or scope to --stage X\n"
    "(single small files, no recursive list burst). If you KNOW 0 stage-apps are writing to\n"
    "this volume, prefix the command with GENOMICS_F16_ACK=1.\n".format(n=len(live))
)
sys.exit(2)
'
rc=$?
# Only the intentional block (2) propagates; crash/other (1, etc.) fails open.
[ "$rc" = "2" ] && exit 2
exit 0
