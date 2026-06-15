#!/usr/bin/env python3
"""Steer / interaction miner — full-corpus transcript mining via Composer 2.5 (cheap, parallel).

The full-coverage, multi-signal counterpart to /observe's recent-window analysis. Mines Claude Code
session transcripts for human-agent interaction signals:
  - steer        : a mid-session correction/redirect/constraint/taste call  -> preference vectors -> GOALS
  - confirmation : explicit approval (the + preference signal nobody mines)  -> sharpens the autonomy boundary
  - agent_miss   : a concrete agent mistake / violated discipline            -> /observe + which-hook-to-build

Pipeline: agentlogs.db universe -> extract (collapse tool noise) -> FREE human-turn pre-filter (skip
autonomous sessions) -> Composer 2.5 ask-mode (parallel) -> JSONL -> scanned-ledger keyed by
(vendor, session) for idempotent / incremental re-runs.

Cost ~ $0.085 per interactive session (Composer $0.50/M in, $2.50/M out; cacheRead counted at full
input rate = conservative upper bound). Budget-capped. NOTE: >3 workers overshoots the cap by
~$0.5-0.8 (in-flight calls finish past the cut) — keep workers <=3 for a tight budget.

Usage:
  uv run python3 mine_steers.py --from-agentlogs --prompt-mode multi --budget 5 --out signals.jsonl
  uv run python3 mine_steers.py --from-agentlogs --prompt-mode steers --per-month 25 --workers 3
Requires: cursor-agent (`agent`) logged in (Cursor subscription); ~/.claude/agentlogs.db.
Re-runs skip already-scanned sessions via the ledger, so a daily incremental pass is ~free.
"""
import json, os, sys, subprocess, threading, random, argparse, sqlite3
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

STATE_DIR = os.path.expanduser("~/.claude/steer-mining")
WS = os.path.join(STATE_DIR, "ws")
os.makedirs(WS, exist_ok=True)
AGENTLOGS = os.path.expanduser("~/.claude/agentlogs.db")
PROJECTS = os.path.expanduser("~/.claude/projects")

INSTR = """You are mining a Claude Code session transcript for STEERS — the human user's interventions that corrected, redirected, constrained, or course-corrected the AI agent mid-session. A steer is any USER message that pushes the agent off the path it was on toward a different one: corrections ("no, do X instead"), constraint injection, taste/judgment calls, disconfirmation ("that's wrong because..."), scope changes, "actually...", or rejection of an approach.
NOT steers: the first task-setting message; pure continuations ("go on","continue","yes","ok") unless they ALSO redirect; tool results.
Output STRICT JSONL, one object per steer, no prose, no fences:
{"quote":"<user's steering words, trimmed>","before":"<one line: what the agent was doing that this redirected>","vector":"<one line: the underlying preference/principle the steer pushed toward>","type":"correction|constraint|taste|redirect|disconfirmation|scope"}
If zero steers, output exactly: NONE"""

MULTI_INSTR = """You are mining a Claude Code session transcript for HUMAN-AGENT INTERACTION SIGNALS. The full session is loaded; pull every signal of these three kinds. Output STRICT JSONL, one object per signal, no prose, no fences. Every object has a "kind" field.
1. STEER — a USER message that corrected/redirected/constrained the agent mid-session (NOT the first task message; NOT pure continuations like "go on"/"yes").
   {"kind":"steer","quote":"<user words>","before":"<what the agent was doing>","vector":"<the preference/principle pushed toward>","type":"correction|constraint|taste|redirect|disconfirmation|scope"}
2. CONFIRMATION — a USER message that explicitly approved, praised, or accepted an agent choice (the positive preference signal; silence does NOT count).
   {"kind":"confirmation","quote":"<user words>","what_approved":"<the agent choice endorsed>","vector":"<the preference this reveals>"}
3. AGENT_MISS — a concrete agent mistake, wasted loop, over-build, over-ask, ignored rule, or dead-end that the user had to correct OR that visibly wasted effort. One per distinct miss.
   {"kind":"agent_miss","what":"<the mistake>","why":"<root cause / the discipline it violated>","triggered_steer":true|false}
If the transcript is an autonomous agent run with no human interaction, output exactly: NONE"""

ACTIVE_INSTR = INSTR


def blocks_text(content):
    if isinstance(content, str): return content
    if isinstance(content, list):
        out = []
        for b in content:
            if isinstance(b, dict):
                t = b.get("type")
                if t == "text": out.append(b.get("text", ""))
                elif t == "tool_use": out.append(f"[tool_use:{b.get('name','')}]")
                elif t == "tool_result": out.append("[tool_result]")
            else: out.append(str(b))
        return "\n".join(out)
    return str(content)


def extract(path):
    turns = []; n_prose = 0
    try: fh = open(path, encoding="utf-8", errors="ignore")
    except Exception: return None, 0
    for line in fh:
        line = line.strip()
        if not line: continue
        try: ev = json.loads(line)
        except Exception: continue
        if ev.get("type") not in ("user", "assistant"): continue
        msg = ev.get("message", {}) or {}
        role = msg.get("role", ev["type"])
        txt = blocks_text(msg.get("content", "")).strip()
        if not txt: continue
        if role == "user" and not txt.startswith("[tool_result]"):
            n_prose += 1
        turns.append(f"\n### {role.upper()}\n{txt}")
    out = "".join(turns)
    if len(out) > 200000: out = out[:200000] + "\n[...truncated...]"
    return out, n_prose


def cost_of(u):
    return (u.get("inputTokens", 0) + u.get("cacheReadTokens", 0)) * 0.5e-6 + u.get("outputTokens", 0) * 2.5e-6


def candidates_from_agentlogs(db, min_lines, vendor):
    """(month, lines, path) for interactive sessions, ordered by start_ts."""
    con = sqlite3.connect(db)
    rows = []
    for ts, lines, root, uuid in con.execute(
            "select start_ts, transcript_lines, project_root, session_uuid from sessions "
            "where vendor=? and transcript_lines>=? and session_uuid is not null order by start_ts",
            (vendor, min_lines)):
        d = (root or "").replace("/", "-")
        f = (uuid or "").replace(vendor + ":", "") + ".jsonl"
        rows.append((ts[:7], str(lines), os.path.join(PROJECTS, d, f)))
    con.close()
    return rows


lock = threading.Lock()
state = {"spent": 0.0, "scanned": 0, "skipped": 0, "steers": 0, "err": 0, "already": 0}
scanned_keys = set()
ledger_fh = None


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record(vendor, session, status, n, cost):
    with lock:
        key = vendor + ":" + session
        if key in scanned_keys:
            return
        scanned_keys.add(key)
        if ledger_fh:
            ledger_fh.write(json.dumps({"vendor": vendor, "session": session, "status": status,
                                        "n_signals": n, "cost": round(cost, 5), "scanned_at": _now()}) + "\n")
            ledger_fh.flush()


def process(rec, budget, out_fh, vendor):
    month, _lines, path = rec
    session = os.path.basename(path)[:-6]
    with lock:
        if (vendor + ":" + session) in scanned_keys:
            state["already"] += 1
            return ("already", month, 0)
        if state["spent"] >= budget:
            return ("budget", month, 0)
    md, nprose = extract(path)
    if md is None or nprose < 2:
        with lock: state["skipped"] += 1
        record(vendor, session, "skip_no_human", 0, 0.0)
        return ("skip", month, 0)
    mdpath = os.path.join(WS, session + ".md")
    open(mdpath, "w", encoding="utf-8").write(md)
    prompt = ACTIVE_INSTR + f"\n\nRead the file {session}.md in this workspace and extract from it per the spec above."
    try:
        res = subprocess.run(["agent", "-p", "--mode", "ask", "--trust", "--model", "composer-2.5",
                              "--output-format", "json", "--workspace", WS, prompt],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
        obj = json.loads(res.stdout)
    except Exception:
        with lock: state["err"] += 1
        record(vendor, session, "err", 0, 0.0)
        return ("err", month, 0)
    finally:
        try: os.remove(mdpath)
        except Exception: pass
    u = obj.get("usage", {}); c = cost_of(u)
    signals = []
    for ln in obj.get("result", "").splitlines():
        ln = ln.strip()
        if ln.startswith("{"):
            try: signals.append(json.loads(ln))
            except Exception: pass
    with lock:
        state["spent"] += c; state["scanned"] += 1; state["steers"] += len(signals)
        for s in signals:
            s["_month"] = month; s["_session"] = session
            out_fh.write(json.dumps(s, ensure_ascii=False) + "\n")
        out_fh.flush()
    record(vendor, session, "ok", len(signals), c)
    return ("ok", month, len(signals))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", help="TSV: month<TAB>lines<TAB>path. Or use --from-agentlogs.")
    ap.add_argument("--from-agentlogs", action="store_true", help="Build the session list from agentlogs.db.")
    ap.add_argument("--db", default=AGENTLOGS)
    ap.add_argument("--vendor", default="claude")
    ap.add_argument("--min-lines", type=int, default=40, help="Pre-filter: skip tiny (autonomous) sessions.")
    ap.add_argument("--out", required=True)
    ap.add_argument("--budget", type=float, default=4.5)
    ap.add_argument("--per-month", type=int, default=0, help="Stratified sample N per month (0 = all).")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--prompt-mode", default="multi", choices=["steers", "multi"])
    ap.add_argument("--ledger", default=os.path.join(STATE_DIR, "scanned_ledger.jsonl"))
    a = ap.parse_args()
    global ACTIVE_INSTR, ledger_fh
    ACTIVE_INSTR = MULTI_INSTR if a.prompt_mode == "multi" else INSTR

    if a.from_agentlogs:
        rows = candidates_from_agentlogs(a.db, a.min_lines, a.vendor)
    elif a.candidates:
        rows = []
        for line in open(a.candidates, encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) >= 3: rows.append((p[0], p[1], p[2]))
    else:
        sys.exit("need --from-agentlogs or --candidates")

    random.seed(a.seed)
    if a.per_month > 0:
        bym = {}
        for r in rows: bym.setdefault(r[0], []).append(r)
        work = []
        for m in sorted(bym):
            rs = bym[m][:]; random.shuffle(rs); work += rs[:a.per_month]
    else:
        random.shuffle(rows); work = rows
    bymc = {}
    for r in work: bymc[r[0]] = bymc.get(r[0], 0) + 1

    os.makedirs(os.path.dirname(a.ledger), exist_ok=True)
    if os.path.exists(a.ledger):
        for ln in open(a.ledger, encoding="utf-8"):
            try: scanned_keys.add(json.loads(ln)["vendor"] + ":" + json.loads(ln)["session"])
            except Exception: pass
    ledger_fh = open(a.ledger, "a", encoding="utf-8")
    sys.stderr.write(f"work={len(work)} by_month={bymc} budget=${a.budget} mode={a.prompt_mode} "
                     f"ledger_known={len(scanned_keys)}\n"); sys.stderr.flush()
    out_fh = open(a.out, "w", encoding="utf-8")
    pms = {}; pmc = {}
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(process, r, a.budget, out_fh, a.vendor) for r in work]
        for f in as_completed(futs):
            tag, month, n = f.result()
            if tag == "ok":
                pms[month] = pms.get(month, 0) + n; pmc[month] = pmc.get(month, 0) + 1
    out_fh.close()
    sys.stderr.write(f"\nDONE spent=${state['spent']:.3f} scanned={state['scanned']} "
                     f"skipped_no_human={state['skipped']} already_in_ledger={state['already']} "
                     f"errors={state['err']} signals={state['steers']}\n")
    for m in sorted(pmc):
        sc = pmc[m]; st = pms.get(m, 0)
        sys.stderr.write(f"  {m}: {sc} scanned, {st} signals, {st/max(sc,1):.2f}/session\n")
    sys.stderr.flush()


if __name__ == "__main__":
    main()
