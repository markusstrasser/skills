#!/usr/bin/env bash
# stop-verify-claims.sh — Deterministic claim verification at stop time.
# Checks if the agent's final message claims work (commits, file creation, tests)
# that can't be confirmed by git state. Replaces the broken prompt hook.
# Blocks only on clear evidence of unverified claims. Fails open.

trap 'exit 0' ERR

INPUT=$(cat)

OUTPUT=$(echo "$INPUT" | python3 -c '
import sys, json, os, re, subprocess

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if data.get("stop_hook_active", False):
    sys.exit(0)

cwd = data.get("cwd", "")
if not cwd:
    sys.exit(0)

msg = data.get("last_assistant_message", "")
if not msg:
    sys.exit(0)

# Patterns that indicate the agent claims to have committed something
# THIS turn (present-tense, first-person). Past-tense citations of earlier
# commits ("the commit from this morning", "all 9 commits exist on main")
# are NOT claims and must not trip the gate. Empirical false-positive rate
# from the unrestricted form was ~50% in long sessions citing earlier work.
COMMIT_CLAIMS = re.compile(
    r"\b("
    r"just\s+(?:committed|pushed|wrote\s+the\s+commit)|"
    r"now\s+(?:committed|pushed)|"
    r"have\s+(?:now\s+|just\s+)?(?:committed|pushed)|"
    # \u2019 = right single quote (smart apostrophe); \u0027 = ASCII apostrophe.
    # Embedded in Python source via \uXXXX escapes so bash single-quoted heredoc
    # does not need its own re-quoting tricks.
    r"i(?:\u2019|\u0027)?(?:ve)?\s+(?:just\s+|now\s+)?(?:committed|pushed)|"
    r"committing\s+(?:now|the|these|this)|"
    r"pushing\s+(?:now|the|these|this)"
    r")\b",
    re.IGNORECASE,
)
# If the matched commit-claim phrase is near a historical marker, treat it
# as a citation, not a claim. Window: ±60 chars of the regex match.
HISTORICAL_NEAR = re.compile(
    r"\b(earlier|previous(?:ly)?|prior|already|before|yesterday|"
    r"the\s+\w+\s+commit|past\s+commit|cited|from\s+\w+\s+ago|in\s+turn\s+\d|"
    r"this\s+morning|last\s+(?:turn|session|night))\b",
    re.IGNORECASE,
)
FILE_CLAIMS = re.compile(
    r"\b(created|wrote|generated)\s+(?:the\s+)?(?:file|script|hook)\s+`?([^\s`]+)`?",
    re.IGNORECASE,
)
TEST_CLAIMS = re.compile(
    r"\b(tests?\s+(?:pass|passing|succeed|green))\b", re.IGNORECASE
)

problems = []

# Check commit claims against git log.
# Also scan the message for cross-repo commits via `git -C <path>` — the agent
# may have legitimately committed to a sibling repo, which will not show up in
# the cwd log. (No apostrophes in comments: this block is single-quoted in sh.)
match = COMMIT_CLAIMS.search(msg)
# Reject if the regex hit but a historical marker is within ±60 chars — its
# a citation of an earlier commit, not a present claim. Empirical: the long-
# session false-positive rate from this hook was ~50% before this filter.
if match:
    span_start = max(0, match.start() - 60)
    span_end = min(len(msg), match.end() + 60)
    nearby = msg[span_start:span_end]
    if HISTORICAL_NEAR.search(nearby):
        match = None
if match:
    try:
        sid_path = os.path.join(cwd, ".claude", "current-session-id")
        if os.path.isfile(sid_path):
            session_start = int(os.path.getmtime(sid_path))
            repos_to_check = [cwd]
            # Collect candidate repo paths mentioned in the message. The agent
            # may refer to a sibling repo via `git -C <path>` OR more loosely as
            # `~/Projects/<name>` or an absolute path. We gather all candidates
            # and later filter to those that are real git repos.
            candidates = []
            for m in re.finditer(r"git\s+-C\s+(?:\"([^\"]+)\"|(\S+))", msg):
                candidates.append(m.group(1) or m.group(2))
            # Home-relative paths: ~/foo, ~/foo/bar (stop at whitespace or backtick)
            for m in re.finditer(r"~/[\w\-./]+", msg):
                candidates.append(m.group(0))
            # Absolute paths under common project roots
            for m in re.finditer(r"/Users/[\w\-./]+", msg):
                candidates.append(m.group(0))
            for raw in candidates:
                p = os.path.expanduser(raw.rstrip(".,;:)`"))
                # Walk up to find a .git dir so sub-paths still resolve to the repo root
                probe = p
                for _ in range(6):
                    if os.path.isdir(os.path.join(probe, ".git")):
                        if probe not in repos_to_check:
                            repos_to_check.append(probe)
                        break
                    parent = os.path.dirname(probe)
                    if not parent or parent == probe:
                        break
                    probe = parent

            verified = False
            for repo in repos_to_check:
                if not os.path.isdir(os.path.join(repo, ".git")):
                    continue
                r = subprocess.run(
                    ["git", "log", "--since", str(session_start), "--format=%H"],
                    cwd=repo, capture_output=True, text=True, timeout=5,
                )
                if r.returncode == 0 and r.stdout.strip():
                    verified = True
                    break
            if not verified:
                problems.append("Claims commits but no commits found in this session")
    except Exception:
        pass

# Check file creation claims against filesystem
for m in FILE_CLAIMS.finditer(msg):
    filepath = m.group(2).rstrip(".,;)")
    # Try relative to cwd
    full = os.path.join(cwd, filepath) if not os.path.isabs(filepath) else filepath
    if not os.path.exists(full):
        # Also try expanding ~
        expanded = os.path.expanduser(filepath)
        if not os.path.exists(expanded):
            problems.append(f"Claims created `{filepath}` but file not found")

if not problems:
    sys.exit(0)

reason_text = "UNVERIFIED CLAIMS:\n" + "\n".join(f"  - {p}" for p in problems) + "\n\nVerify or correct before stopping."
output = {
    "decision": "block",
    "reason": reason_text,
}
print(json.dumps(output))
' 2>/dev/null)

if [[ -n "$OUTPUT" ]]; then
    ~/Projects/skills/hooks/hook-trigger-log.sh "verify-claims" "block" "unverified claims" 2>/dev/null || true
    echo "$OUTPUT"
fi

exit 0
