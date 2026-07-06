#!/usr/bin/env bash
# posttool-session-touched-log.sh — record files THIS session wrote, per session_id.
#
# Why: stop-research-gate (and any session-scoped gate) needs to distinguish files
# the CURRENT session wrote from files a CONCURRENT session created mid-run. The
# session-start dirty-baseline can't catch peer files created AFTER start. This
# logger appends every Write/Edit/MultiEdit target to /tmp/session-touched-<id>.txt
# so the gate can positively attribute a file to this session.
#
# Append-only, best-effort, fails open. Trivial perf (one echo per file write).
# Deploy as PostToolUse hook with matcher Write|Edit|MultiEdit.
INPUT=$(cat) || exit 0
echo "$INPUT" | python3 -c "
import sys, json, os, re
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
if d.get('tool_name','') not in ('Write','Edit','MultiEdit'):
    sys.exit(0)
sid = (d.get('session_id') or '').strip()
if not sid or not re.match(r'^[A-Za-z0-9._-]+\$', sid):
    sys.exit(0)  # no/garbage session id -> can't key; fail open
fp = (d.get('tool_input',{}) or {}).get('file_path','') or ''
if not fp:
    sys.exit(0)
# store repo-relative when possible so it matches the gate's git-derived paths
cwd = d.get('cwd','') or ''
rel = fp
if cwd and fp.startswith(cwd.rstrip('/') + '/'):
    rel = fp[len(cwd.rstrip('/'))+1:]
try:
    with open(f'/tmp/session-touched-{sid}.txt','a') as fh:
        fh.write(rel + '\n')
except OSError:
    pass
# Content hash at write time -> /tmp/session-touched-<sid>.hashes.txt (path\thash).
# Consumer: stop-uncommitted-warn.sh commits a my_touched file ONLY if its current
# content still matches the owner's last-written hash — a later mutation by a peer
# session or an unledgered subprocess makes it contested-by-content and DEFERRED,
# never swept (2026-07-06: peer checkpoint 0a2873a committed another session's
# justfile/HINDSIGHT content because path-ownership from hours earlier never expired).
try:
    import hashlib
    with open(fp, 'rb') as fh:
        h = hashlib.sha256(fh.read()).hexdigest()
    with open(f'/tmp/session-touched-{sid}.hashes.txt','a') as fh:
        fh.write(f'{rel}\t{h}\n')
except OSError:
    pass
" 2>/dev/null
exit 0
