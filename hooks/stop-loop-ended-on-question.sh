#!/usr/bin/env bash
# stop-loop-ended-on-question.sh — thin wrapper for the SHADOW detector (logic in the .py).
# SHADOW MODE: logs would-fire rows, never blocks. See stop_loop_ended_on_question.py header.
trap 'exit 0' ERR
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$DIR/stop_loop_ended_on_question.py" || true
exit 0
