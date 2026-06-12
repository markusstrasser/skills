#!/usr/bin/env bash
# pretool-heavy-load-guard.sh — PreToolUse(Bash) advisory.
# Warns (never blocks) before launching a HEAVY LOCAL compute job while the
# machine is already contended. The structural fix for the recurring "launched a
# heavy batch into high load → thrash / hard reboot" failure that a memory note
# (reference_throttle_heavy_local_batches) kept failing to prevent — per the
# global pair-rule, a recurring discipline failure wants a hook, not another note.
#
# Warn-not-block by design: it injects context so the agent CHOOSES to defer /
# throttle / move to Modal, without ever denying a command the user intends.
# Never exits non-zero.
trap 'exit 0' ERR

data="$(cat 2>/dev/null)" || exit 0
cmd="$(printf '%s' "$data" | jq -r '.tool_input.command // ""' 2>/dev/null || true)"
[ -z "$cmd" ] && exit 0

# Heavy LOCAL compute jobs (NOT remote — modal/cloud offload is the FIX, not the
# problem). Conservative all-list so this stays quiet on ordinary commands.
HEAVY_RE='generate_unified_embeddings|generate_gemini_embeddings|extract_media|extract_media_phenotype|rebuild_identity|identity[._]rebuild|20260610j|p4_identity|marker_single|local.*marker|ffmpeg|transcribe|voxtral|whisper|late_chunking|build_certs|rebuild_image_embeddings|sentence-transformers|\.embed\b|embed\.py|rerank=True|CrossEncoder|reranker|SearchEngine|fs_recall|fs_hard|emb_rerank|recall_eval|recall_bakeoff|fs_ab'
echo "$cmd" | grep -qiE "$HEAVY_RE" || exit 0
# A backgrounded job that offloads is fine; a foreground local grind is the risk.
echo "$cmd" | grep -qiE 'modal (run|deploy)|--remote' && exit 0

# --- Concurrency cap (BLOCK) — the 2026-06-10 OOM-freeze fix ---------------------
# Three parallel torch eval jobs (each: embedding model + cross-encoder over a full
# index, with PYTORCH_ENABLE_MPS_FALLBACK=1 spilling oversized tensors to CPU RAM)
# hit ~44GB on this 36GB Mac → 4 OOM sweeps → freeze → forced power-button reboot.
# Cap heavy local model jobs to ONE at a time. Signal is name-independent: any python
# already resident >2GB IS a model job in flight, so a second heavy launch is blocked.
# RAM-bomb backstop (name-independent, ~0 false positive): a python already resident
# >8GB IS a torch model job in flight — normal python / MCP servers never reach that.
# (A pgrep NAME match was tried and removed: command lines carry these keywords as
# prompt/discussion TEXT, so it false-blocked unrelated work — the exact iatrogenic harm
# we're preventing. RSS is the only honest signal here.)
RUNNING_HUGE="$(ps -axo rss=,pid=,comm= 2>/dev/null | awk '$1>8388608 && tolower($3) ~ /python/ {printf "PID %s ~%.0fGB; ", $2, $1/1048576}')"
if [ -n "$RUNNING_HUGE" ]; then
  {
    echo "BLOCKED: a python job is already holding >8GB RAM ($RUNNING_HUGE) — a model job in flight."
    echo "Cap local model-loading jobs to ONE AT A TIME. On 2026-06-10 three parallel torch eval"
    echo "jobs (embedding model + cross-encoder over a full index, MPS-fallback spilling to RAM)"
    echo "consumed ~44GB on this 36GB Mac → OOM freeze → forced reboot. Wait for it or kill it."
    echo "Inspect: ps -axo rss,pid,command | sort -rn | head"
  } >&2
  exit 2
fi
# --- MPS-fallback footgun (WARN) -------------------------------------------------
# PYTORCH_ENABLE_MPS_FALLBACK=1 silently spills tensors MPS can't hold into CPU RAM
# (the "Materializing param…" 14GB/proc spill). Without it, an oversized tensor errors
# cleanly instead of eating RAM. Fold into the advisory context emitted below.
MPS_NOTE=""
echo "$cmd" | grep -q "PYTORCH_ENABLE_MPS_FALLBACK" && MPS_NOTE="PYTORCH_ENABLE_MPS_FALLBACK=1 silently spills oversized tensors into CPU RAM (14GB/proc, 2026-06-10) — drop it so they error cleanly. "

CORES="$(sysctl -n hw.ncpu 2>/dev/null || echo 8)"
LOAD1="$(sysctl -n vm.loadavg 2>/dev/null | tr -d '{}' | awk '{print $1}')"
[ -z "$LOAD1" ] && LOAD1="$(uptime | sed -E 's/.*averages?: *//' | awk '{print $1}')"
CLAUDES="$(pgrep -c -f 'claude' 2>/dev/null || echo 1)"

# Warn only when genuinely contended: 1-min load above core count (≥1.0/core),
# or many concurrent agents. Below that, a heavy job is fine — stay silent.
warn="$(CORES="$CORES" LOAD1="$LOAD1" CLAUDES="$CLAUDES" python3 -c "
import os
cores=float(os.environ['CORES']); load=float(os.environ['LOAD1'] or 0); n=int(os.environ['CLAUDES'] or 1)
if load > cores or n >= 4:
    print(f'Compute preflight: 1-min load {load:.1f} on {int(cores)} cores'
          + (f', {n} claude procs' if n>=4 else '')
          + '. This is a HEAVY LOCAL job — launching now risks thrash/starvation '
            '(see reference_throttle_heavy_local_batches: a prior such launch hard-rebooted the Mac). '
            'Prefer: throttle workers to 4-6, defer until load < {0}, or offload to Modal.'.format(int(cores)))
" 2>/dev/null)"
# Surface the MPS-fallback footgun even when load is fine (it's a per-proc RAM bomb,
# not a contention issue).
warn="${MPS_NOTE}${warn}"
[ -z "$warn" ] && exit 0

python3 -c "import json,sys; print(json.dumps({'additionalContext': sys.argv[1]}))" "$warn"

TRIG="$HOME/Projects/skills/hooks/hook-trigger-log.sh"
[ -x "$TRIG" ] && "$TRIG" "heavy-load-guard" "warn" "load=$LOAD1 cores=$CORES claudes=$CLAUDES" 2>/dev/null || true
exit 0
