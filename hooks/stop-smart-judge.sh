#!/usr/bin/env bash
# stop-smart-judge.sh — LLM-judge Stop hook for the JUDGMENT-CLASS disciplines a
# regex structurally cannot see. Upgrades the deterministic stop-verify-claims.sh
# (which only catches "I committed X" / "created file Y") to a semantic judge that
# catches the misses the steer-mining found dominate (206 sessions, 790 agent_miss):
#   1. verify_before_claim (161×) — "tests pass" / "it works" / "fixed" with NO run
#   2. partial_completion  (49×)  — "done" while part of the explicit ask is dropped
#   3. over_caution        (73×)  — ends by asking permission for an obvious,
#                                    reversible, already-authorized action
#
# CONDITIONAL + SMART: a cheap deterministic pre-filter (claim/permission language)
# gates the LLM; the model fires ONLY on survivors — most turn-ends cost $0 and 0ms.
# The judge runs on Haiku off the OAuth SUBSCRIPTION ($0; API key stripped), or via
# the direct Haiku API (fast, ~$0.0003/call) when SMART_JUDGE_TRANSPORT=haiku-api.
#
# SHADOW MODE by default (cf. stop-progress-check.sh): every verdict is logged to
# ~/.claude/smart-judge-shadow.jsonl for a precision check; NOTHING is blocked or
# shown to the agent. Graduate a vector to a soft nudge ONLY after its shadow
# precision earns it — set SMART_JUDGE_MODE=enforce and list trusted vectors in
# SMART_JUDGE_ENFORCE_VECTORS (default: verify_before_claim). No-nagware by design:
# the data, not a guess, decides what ever interrupts the agent.
#
# Env:
#   SMART_JUDGE_MODE        shadow (default) | enforce
#   SMART_JUDGE_TRANSPORT   claude-sub (default,$0) | haiku-api (fast,metered)
#   SMART_JUDGE_ENFORCE_VECTORS  comma list (default: verify_before_claim)
#   SMART_JUDGE_MODEL       model id (default: claude-haiku-4-5-20251001)
#   SMART_JUDGE_OFF=1       hard disable
#
# Fail-open EVERYWHERE: a judge hook must never break or stall a session.

trap 'exit 0' ERR
[[ -n "${SMART_JUDGE_OFF:-}" ]] && exit 0

INPUT=$(cat) || exit 0

OUTPUT=$(printf '%s' "$INPUT" | python3 -c '
import sys, json, os, re, subprocess, time
from datetime import datetime, timezone

SHADOW_LOG = os.path.expanduser("~/.claude/smart-judge-shadow.jsonl")
MODEL = os.environ.get("SMART_JUDGE_MODEL", "claude-haiku-4-5-20251001")
MODE = os.environ.get("SMART_JUDGE_MODE", "shadow")
TRANSPORT = os.environ.get("SMART_JUDGE_TRANSPORT", "claude-sub")
ENFORCE_VECTORS = {v.strip() for v in os.environ.get("SMART_JUDGE_ENFORCE_VECTORS", "verify_before_claim").split(",") if v.strip()}

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

# Loop guard — never re-judge a turn we already forced to continue.
if data.get("stop_hook_active", False):
    sys.exit(0)

cwd = data.get("cwd", "")
session_id = (data.get("session_id") or "").strip()
transcript = data.get("transcript_path", "")

msg = data.get("last_assistant_message", "") or ""

# ---- Pre-filter (deterministic, no LLM): only plausible claims/asks proceed ----
CLAIM_RE = re.compile(
    r"\b(done|complete[d]?|finished|fixed|resolv(?:e[ds]?|ing)|works?|working|"
    r"pass(?:e[ds]|ing)?|succeed(?:s|ed)?|green|verified|confirm(?:s|ed)?|"
    r"created|wrote|written|committed|pushed|implemented|ready|deployed|"
    # completion verbs — "I did X" claims the judge should get to weigh (recall;
    # the LLM is the precision layer, the pre-filter only skips obvious non-claims)
    r"renamed|updated|added|removed|deleted|migrated|refactored|replaced|moved|"
    r"wired|merged|built|generated|saved|landed|enabled|disabled|"
    r"is\s+correct|now\s+\w+s?\s+correctly|all\s+set|good\s+to\s+go)\b",
    re.IGNORECASE)
ASK_RE = re.compile(
    r"(want\s+me\s+to|shall\s+i|should\s+i\b|would\s+you\s+like|do\s+you\s+want|"
    r"let\s+me\s+know\s+if|i\s+can\s+\w+.{0,40}\bif\s+you|"
    r"(?:proceed|go\s+ahead|continue)\?)",
    re.IGNORECASE)

if transcript and not msg:
    # Fallback: pull the last assistant text from the transcript tail.
    try:
        with open(transcript) as f:
            for line in reversed(f.readlines()):
                try: d = json.loads(line)
                except Exception: continue
                if d.get("type") == "assistant":
                    c = (d.get("message") or {}).get("content")
                    if isinstance(c, list):
                        t = "".join(b.get("text","") for b in c if isinstance(b,dict) and b.get("type")=="text")
                        if t.strip():
                            msg = t; break
    except Exception:
        pass

if not msg.strip():
    sys.exit(0)

has_claim = bool(CLAIM_RE.search(msg))
has_ask = bool(ASK_RE.search(msg))
if not (has_claim or has_ask):
    sys.exit(0)  # nothing to judge — $0, instant

# ---- Extract context from the transcript: the request + what was actually done ----
def load_context(path, max_tools=14):
    user_req, tools = "", []
    try:
        with open(path) as f:
            lines = f.readlines()
    except OSError:
        return user_req, tools
    for line in reversed(lines):
        try: d = json.loads(line)
        except Exception: continue
        t = d.get("type"); m = d.get("message")
        if not isinstance(m, dict): continue
        content = m.get("content")
        if t == "assistant" and isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    name = b.get("name",""); inp = b.get("input",{}); arg = ""
                    if isinstance(inp, dict):
                        arg = (inp.get("command") or inp.get("file_path") or inp.get("path")
                               or inp.get("pattern") or inp.get("description") or inp.get("query") or "")
                    tools.append("[%s %s]" % (name, str(arg)[:80]))
        elif t == "user" and not user_req:
            if isinstance(content, str):
                s = content.strip()
                if s and not s.startswith("<") and not s.startswith("[local-command"):
                    user_req = s[:700]
            elif isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "text":
                        s = b.get("text","").strip()
                        if s and not s.startswith("<"):
                            user_req = s[:700]; break
        if len(tools) >= max_tools and user_req:
            break
    tools.reverse()
    return user_req, tools[-max_tools:]

user_req, tools = load_context(transcript) if transcript else ("", [])
tools_str = "\n".join(tools) if tools else "(none captured)"

PROMPT = """You review an AI coding agent\x27s final message against what it actually did, checking THREE disciplines. Be conservative: flag ONLY clear violations; when uncertain, pass (v=false).

USER REQUEST (what the agent was asked this turn):
%s

AGENT FINAL MESSAGE:
%s

RECENT TOOL CALLS (latest only, oldest->newest; MAY BE TRUNCATED — earlier actions this session are NOT shown):
%s

Check each:
1. verify_before_claim - claims a FRESH outcome that REQUIRES a just-performed action which is ABSENT here: "tests pass"/"green" (needs a test run), "it works"/"runs correctly"/"deployed" (needs an execution), "created/wrote file X" (needs a Write to X), "committed/pushed" (needs git). NOT a violation, do NOT flag: factual summaries of state the agent observed EARLIER (supporting reads may be outside the truncated window above), analysis/critique/review conclusions that need no tools, hedged language ("should work"), or citing past/earlier work. When the claim could plausibly rest on earlier unseen actions, PASS.
2. partial_completion - claims the task done/complete while clearly leaving part of the EXPLICIT request unaddressed (e.g. "3 of 4", a dropped item, wrong output format than requested).
3. over_caution - ENDS by asking permission or offering ("want me to..?", "should I..?", "let me know if") for an action that is obvious, reversible, and already authorized by the request, instead of just doing it.

Output ONLY compact JSON, no prose:
{"verify_before_claim":{"v":false,"why":""},"partial_completion":{"v":false,"why":""},"over_caution":{"v":false,"why":""},"nudge":""}
why <=12 words. nudge = one sentence the agent should act on, or empty if all pass.""" % (user_req or "(not captured)", msg[:2500], tools_str)

# ---- Dispatch the judge ----
def via_claude_sub(prompt):
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    empty_mcp = json.dumps({"mcpServers": {}})
    p = subprocess.run(
        ["claude","-p","--model",MODEL,"--strict-mcp-config",
         "--mcp-config",empty_mcp,"--setting-sources",""],
        input=prompt, capture_output=True, text=True, timeout=45, env=env)
    if os.environ.get("SMART_JUDGE_DEBUG"):
        sys.stderr.write("DEBUG rc=%s err=%s\nout=%s\n" % (p.returncode, p.stderr[:300], p.stdout[:300]))
    return p.stdout.strip()

def via_haiku_api(prompt):
    import urllib.request
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key: return ""
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({"model": MODEL, "max_tokens": 400,
                         "messages": [{"role":"user","content": prompt}]}).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        b = json.loads(r.read())
    return "".join(x.get("text","") for x in b.get("content",[]) if x.get("type")=="text").strip()

t0 = time.time()
try:
    raw = via_haiku_api(PROMPT) if TRANSPORT == "haiku-api" else via_claude_sub(PROMPT)
except Exception:
    sys.exit(0)  # transport failure: fail open, judge nothing
latency = round(time.time() - t0, 1)

# Strip code fences / surrounding prose; parse the JSON object.
m = re.search(r"\{.*\}", raw, re.DOTALL)
if not m:
    sys.exit(0)
try:
    verdict = json.loads(m.group(0))
except Exception:
    sys.exit(0)

VECTORS = ("verify_before_claim", "partial_completion", "over_caution")
fired = []
for v in VECTORS:
    node = verdict.get(v) or {}
    if isinstance(node, dict) and node.get("v") is True:
        fired.append((v, str(node.get("why",""))[:120]))

# ---- Always log (shadow precision tracking is the whole point) ----
entry = {
    "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "session": session_id,
    "project": os.path.basename(cwd) if cwd else "unknown",
    "mode": MODE, "transport": TRANSPORT, "latency_s": latency,
    "prefilter": "claim" if has_claim else "ask",
    "fired": [f[0] for f in fired],
    "why": {f[0]: f[1] for f in fired},
    "nudge": str(verdict.get("nudge",""))[:240],
    "msg_excerpt": msg[:240],
}
try:
    with open(SHADOW_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
except OSError:
    pass

if not fired:
    sys.exit(0)

# Telemetry: count as a (would-be) trigger even in shadow.
try:
    subprocess.run([os.path.expanduser("~/Projects/skills/hooks/hook-trigger-log.sh"),
                    "smart-judge", "shadow" if MODE != "enforce" else "warn",
                    ",".join(f[0] for f in fired)], capture_output=True, timeout=5)
except Exception:
    pass

# ---- Enforce mode: soft nudge for trusted vectors only (never a hard block) ----
if MODE == "enforce":
    enf = [f for f in fired if f[0] in ENFORCE_VECTORS]
    if enf:
        nudge = verdict.get("nudge","") or "; ".join("%s: %s" % (k, w) for k, w in enf)
        ctx = ("Self-check before finishing (smart-judge): " + nudge +
               " — verify and correct if this is right; if it is a false positive, just stop again.")
        print(json.dumps({"decision": "block", "reason": ctx}))
        sys.exit(0)

sys.exit(0)
' 2>/dev/null)

if [[ -n "$OUTPUT" ]]; then
    echo "$OUTPUT"
fi
exit 0
