#!/usr/bin/env python3
"""Rank agent_miss signals from mine_steers output → which-hook-to-build-first.

The ACT half of the steer-mining loop: mine_steers.py emits raw signals (steer /
confirmation / agent_miss); this aggregates the agent_miss kind into a ranked
table of recurring failure CLASSES, each weighted by frequency and whether it
forced a human steer (triggered_steer = real supervision cost).

Deterministic-first: buckets the LLM-provided `why` (root cause) into known
discipline classes via keyword match, and prints the UNCLASSIFIED misses raw so
nothing is silently dropped. A class that recurs is a hook candidate (constitution
principle 11: 10+ → architecture; here we surface the rate so the human/loop
decides).

Usage:
  uv run python3 rank_agent_miss.py ~/.claude/steer-mining/probe-2026-06-16.jsonl
  uv run python3 rank_agent_miss.py FILE --min 2     # only classes with >=2 hits
"""
import json, argparse, collections, re

# Discipline classes drawn from the constitution / global rules failure modes.
# (label, regex over the `why`+`what` text). Order = FIRST MATCH WINS, so the
# more specific patterns are listed before the generic ones. Tightened 2026-06-17
# after a 31-session probe left 55% UNCLASSIFIED — the 5 specific classes below
# (premature-stop, skill-contract, subagent-strand, proxy-no-probe, shared-state)
# were the dominant clusters hiding in UNCLASSIFIED.
CLASSES = [
    ("subagent-strand",        r"subagent.*(exhaust|strand|stub|turn-?budget|budget|unfilled)|stub.*(only|without|file)|skeleton-first|write-stub|left.*(stub|items unfilled)"),
    ("skill-contract-viol",    r"phase ?\d|phase 0\.5|mandatory.*(sweep|phase)|skill.*(contract|dispatch|orchestrat)|binding phase|phase orchestrat|skipped.*phase|re-?invoked"),
    ("shared-state-clobber",   r"shared.*(checkpoint|state|path)|clobber|peer.?session|read-?before-?write|cross-(session|agent)|overwrote.*checkpoint"),
    ("proxy-without-probe",    r"proxy|extrapolat|unprobed|without.*(principal )?probe|denominator|inferred.*(instead|without)"),
    ("premature-stop-defer",   r"declared.*(complete|done|next)|presented.*(complete|done|largely)|deferred?.*(buildable|actionable|immediat|view)|waited rather|premature.*idle|over-?defer|false blocker|without.*prov.*regress|idle posture|stopped and present|closed.*(with|summary)"),
    ("didnt-check-prior-work", r"prior work|already (exist|built|done|ship)|rediscover|reinvent|duplicat|pre-build|check.*exist|read.*(repo|docs|own plan|ops docs)|plan-to-execution|drift.*(plan|execution)|existing.*(script|fast)"),
    ("didnt-verify-claim",     r"verif|unverified|assert.*without|didn'?t (test|check|run)|hallucinat|assumed|unchecked|sanity check|false belief|representative.*sampl|eval discipline"),
    ("over-build",             r"over-?build|over-?engineer|speculative|premature.*(abstract|infra)|built.*no.*caller|yagni|gold-?plat|both paths|offered.*both"),
    ("over-ask",               r"over-?ask|asked.*(instead|rather than)|permission.*(cheap|no-?brainer|reversible)|punt|offered.*instead of"),
    ("wasted-loop-poll",       r"poll|spin|loop|retr(y|ied).*(same|fail)|repeated.*(command|search|read)|flood|serial.*(call|instead)|parallel"),
    ("ignored-rule",           r"ignored.*(rule|lesson|prior)|violated.*(discipline|rule|guard|standard)|routed around|bypass|skipped.*(hook|gate|check)|convention|quoting gotcha"),
    ("premature-converge",     r"premature.*conver|first idea|didn'?t (explore|brainstorm|diverge)|single.*(option|approach)|no alternatives"),
    ("scope-drift",            r"scope|out of scope|beyond.*ask|unasked|unrelated"),
    ("stale-context",          r"stale|outdated|post-?compact|forgot|lost context|didn'?t re-?read"),
]


def classify(text):
    t = text.lower()
    for label, pat in CLASSES:
        if re.search(pat, t):
            return label
    return "UNCLASSIFIED"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--min", type=int, default=1, help="Only show classes with >= N hits.")
    a = ap.parse_args()

    misses = []
    for f in a.files:
        for ln in open(f, encoding="utf-8"):
            ln = ln.strip()
            if not ln.startswith("{"):
                continue
            try:
                o = json.loads(ln)
            except Exception:
                continue
            if o.get("kind") == "agent_miss":
                misses.append(o)

    if not misses:
        print("No agent_miss signals found.")
        return

    buckets = collections.defaultdict(list)
    for m in misses:
        cls = classify((m.get("why", "") + " " + m.get("what", "")))
        buckets[cls].append(m)

    total = len(misses)
    steered = sum(1 for m in misses if m.get("triggered_steer"))
    print(f"agent_miss total={total}  triggered_steer={steered} ({steered*100//max(total,1)}%)\n")

    # Rank: weight = count + count_that_triggered_a_steer (real supervision cost counts double).
    def weight(items):
        return len(items) + sum(1 for m in items if m.get("triggered_steer"))

    ranked = sorted(buckets.items(), key=lambda kv: -weight(kv[1]))
    print(f"{'class':24} {'n':>3} {'steered':>7} {'weight':>6}")
    print("-" * 48)
    for cls, items in ranked:
        if len(items) < a.min:
            continue
        st = sum(1 for m in items if m.get("triggered_steer"))
        print(f"{cls:24} {len(items):>3} {st:>7} {weight(items):>6}")

    # Show the raw misses for the top classes + ALL unclassified (never drop silently).
    print("\n=== detail (top-3 classes + all UNCLASSIFIED) ===")
    show = [c for c, _ in ranked[:3]] + (["UNCLASSIFIED"] if "UNCLASSIFIED" in buckets else [])
    for cls in dict.fromkeys(show):
        print(f"\n## {cls} ({len(buckets[cls])})")
        for m in buckets[cls]:
            flag = "→steer" if m.get("triggered_steer") else ""
            print(f"  - {m.get('what','')[:110]}  [{m.get('why','')[:60]}] {flag}")


if __name__ == "__main__":
    main()
