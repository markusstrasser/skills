#!/usr/bin/env bash
# sessionend-overview-trigger.sh — Trigger overview generation on session end.
# SessionEnd hook. Side-effect only (no decision control). Fails open.
#
# Two-stage logic:
#   1. Route: classify changed files by scope (source, tooling, structure)
#   2. Trigger: composite signal per scope (structural changes, config changes, LOC)
#   3. Execute: shadow mode (log) or live mode (generate)

trap 'exit 0' ERR

INPUT=$(cat)

echo "$INPUT" | python3 -c '
import sys, json, os, subprocess
from datetime import datetime

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

cwd = data.get("cwd", "")
if not cwd or not os.path.isdir(cwd):
    sys.exit(0)

# --- Load project config ---
conf_path = os.path.join(cwd, ".claude", "overview.conf")
if not os.path.isfile(conf_path):
    sys.exit(0)  # Project not opted in

config = {}
with open(conf_path) as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        config[key.strip()] = val.strip().strip("\"")

mode = config.get("OVERVIEW_MODE", "shadow")
configured_types = [t.strip() for t in config.get("OVERVIEW_TYPES", "").split(",") if t.strip()]
if not configured_types:
    sys.exit(0)

loc_threshold = int(config.get("OVERVIEW_LOC_THRESHOLD", "50"))

# --- Get HEAD ---
try:
    head = subprocess.run(
        ["git", "-C", cwd, "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=5
    ).stdout.strip()
except Exception:
    sys.exit(0)

if not head:
    sys.exit(0)

# --- Check per-type markers (skip types already at HEAD) ---
# Legacy migration: if old single marker exists but no per-type markers, use it as fallback
legacy_marker_path = os.path.join(cwd, ".claude", "overview-marker")
legacy_hash = None
if os.path.isfile(legacy_marker_path):
    with open(legacy_marker_path) as f:
        legacy_hash = f.read().strip()

types_needing_update = []
for t in configured_types:
    type_marker = os.path.join(cwd, ".claude", f"overview-marker-{t}")
    if os.path.isfile(type_marker):
        with open(type_marker) as f:
            if f.read().strip() == head:
                continue  # This type is current
    elif legacy_hash == head:
        continue  # Legacy marker says current
    types_needing_update.append(t)

if not types_needing_update:
    sys.exit(0)  # All types are current

# --- Get changed files ---
# Use the oldest per-type marker as diff baseline
oldest_marker = None
for t in types_needing_update:
    type_marker = os.path.join(cwd, ".claude", f"overview-marker-{t}")
    if os.path.isfile(type_marker):
        with open(type_marker) as f:
            oldest_marker = f.read().strip()  # any marker is better than none
            break
if not oldest_marker and legacy_hash:
    oldest_marker = legacy_hash

if oldest_marker:
    diff_range = f"{oldest_marker}..HEAD"
else:
    # First run: use last 20 commits as baseline
    diff_range = "HEAD~20..HEAD"

try:
    # Regular changes
    name_result = subprocess.run(
        ["git", "-C", cwd, "diff", "--name-only", diff_range],
        capture_output=True, text=True, timeout=10
    )
    changed_files = [f for f in name_result.stdout.strip().split("\n") if f]

    # Structural changes (adds, deletes, renames)
    adr_result = subprocess.run(
        ["git", "-C", cwd, "diff", "--diff-filter=ADR", "--name-only", diff_range],
        capture_output=True, text=True, timeout=10
    )
    structural_files = [f for f in adr_result.stdout.strip().split("\n") if f]

    # LOC changes per file
    stat_result = subprocess.run(
        ["git", "-C", cwd, "diff", "--numstat", diff_range],
        capture_output=True, text=True, timeout=10
    )
except Exception:
    sys.exit(0)

# Parse numstat for LOC
loc_by_file = {}
for line in stat_result.stdout.strip().split("\n"):
    if not line:
        continue
    parts = line.split("\t")
    if len(parts) >= 3:
        added = int(parts[0]) if parts[0] != "-" else 0
        removed = int(parts[1]) if parts[1] != "-" else 0
        loc_by_file[parts[2]] = added + removed

# --- Classify files into scopes ---
# Read per-type dir mappings from config
scope_dirs = {}
for t in configured_types:
    key = f"OVERVIEW_{t.upper()}_DIRS"
    dirs_str = config.get(key, "")
    scope_dirs[t] = [d.strip().rstrip("/") for d in dirs_str.split(",") if d.strip()]

# Config/dependency files that signal tooling changes
CONFIG_PATTERNS = {
    "package.json", "pyproject.toml", "bb.edn", "deps.edn", "Cargo.toml",
    "go.mod", "requirements.txt", "setup.py", "setup.cfg", ".claude/settings.json",
}

# Files to skip entirely
SKIP_PREFIXES = ("test/", "tests/", "docs/", ".git/")
SKIP_SUFFIXES = ("_test.py", "_test.go", ".test.js", ".test.ts", ".spec.js", ".spec.ts", ".md")

def classify_file(fpath):
    """Return set of scopes this file belongs to."""
    # Skip test/docs files
    for prefix in SKIP_PREFIXES:
        if fpath.startswith(prefix):
            return set()
    for suffix in SKIP_SUFFIXES:
        if fpath.endswith(suffix):
            return set()

    scopes = set()
    basename = os.path.basename(fpath)

    # Check config files → tooling scope
    if basename in CONFIG_PATTERNS and "tooling" in configured_types:
        scopes.add("tooling")

    # Check per-scope dir mappings
    for scope, dirs in scope_dirs.items():
        for d in dirs:
            if fpath.startswith(d) or fpath == d:
                scopes.add(scope)
                break

    return scopes

# Aggregate per scope
scope_data = {}
for t in configured_types:
    scope_data[t] = {
        "changed_files": 0,
        "structural_files": 0,
        "loc": 0,
        "config_touched": False,
        "trigger_reasons": [],
    }

for f in changed_files:
    scopes = classify_file(f)
    for s in scopes:
        if s in scope_data:
            scope_data[s]["changed_files"] += 1
            scope_data[s]["loc"] += loc_by_file.get(f, 0)
            if os.path.basename(f) in CONFIG_PATTERNS:
                scope_data[s]["config_touched"] = True

for f in structural_files:
    scopes = classify_file(f)
    for s in scopes:
        if s in scope_data:
            scope_data[s]["structural_files"] += 1

# --- Composite trigger per scope ---
triggered_scopes = []
for scope, sd in scope_data.items():
    reasons = []
    struct_count = sd["structural_files"]
    if struct_count >= 1:
        reasons.append("structural:" + str(struct_count))
    if sd["config_touched"]:
        reasons.append("config_file")
    loc_val = sd["loc"]
    if loc_val > loc_threshold:
        reasons.append("loc:" + str(loc_val))

    if reasons:
        sd["trigger_reasons"] = reasons
        triggered_scopes.append(scope)

if not triggered_scopes:
    # No scope triggered — generator will write per-type markers on success.
    # No marker advance here; let accumulated changes build until threshold.
    sys.exit(0)

# --- Log decision ---
session = data.get("session_id", "")
project = os.path.basename(cwd) if cwd else ""
log_entry = {
    "ts": datetime.now().isoformat(timespec="seconds"),
    "session": session,
    "project": project,
    "marker_hash": marker_hash or "initial",
    "head_hash": head,
    "changed_files": len(changed_files),
    "scopes_triggered": triggered_scopes,
    "trigger_reasons": {s: scope_data[s]["trigger_reasons"] for s in triggered_scopes},
    "would_generate": True,
    "lines_changed": {s: scope_data[s]["loc"] for s in configured_types},
    "mode": mode,
}

log_path = os.path.join(cwd, ".claude", "overview-trigger.log")
os.makedirs(os.path.dirname(log_path), exist_ok=True)
with open(log_path, "a") as f:
    f.write(json.dumps(log_entry, separators=(",", ":")) + "\n")

# --- Execute or skip ---
# Generator writes per-type markers on success. No marker write here.
if mode == "live":
    gen_script = os.path.expanduser("~/Projects/skills/hooks/generate-overview.sh")
    if os.path.isfile(gen_script):
        # Single --auto call; generator skips types already at commit-hash
        subprocess.Popen(
            [gen_script, "--auto", "--commit-hash", head, "--project-root", cwd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
'

exit 0
