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
cmd="$(printf '%s' "$data" | python3 -c "import json,sys
try: print(json.load(sys.stdin).get('tool_input',{}).get('command',''))
except Exception: pass" 2>/dev/null)"
[ -z "$cmd" ] && exit 0

# Heavy LOCAL compute jobs (NOT remote — modal/cloud offload is the FIX, not the
# problem). Conservative all-list so this stays quiet on ordinary commands.
HEAVY_RE='generate_unified_embeddings|generate_gemini_embeddings|extract_media|extract_media_phenotype|rebuild_identity|identity[._]rebuild|20260610j|p4_identity|marker_single|local.*marker|ffmpeg|transcribe|voxtral|whisper|late_chunking|build_certs|rebuild_image_embeddings|sentence-transformers|\.embed\b|embed\.py'
echo "$cmd" | grep -qiE "$HEAVY_RE" || exit 0
# A backgrounded job that offloads is fine; a foreground local grind is the risk.
echo "$cmd" | grep -qiE 'modal (run|deploy)|--remote' && exit 0

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
[ -z "$warn" ] && exit 0

python3 -c "import json,sys; print(json.dumps({'additionalContext': sys.argv[1]}))" "$warn"

TRIG="$HOME/Projects/skills/hooks/hook-trigger-log.sh"
[ -x "$TRIG" ] && "$TRIG" "heavy-load-guard" "warn" "load=$LOAD1 cores=$CORES claudes=$CLAUDES" 2>/dev/null || true
exit 0
