"""Epistemic content extraction for PreCompact hook.

Reads hook JSON from stdin (session_id, transcript_path, cwd, trigger).
Outputs:
  1. ~/.claude/compact-log.jsonl — append-only compaction metrics
  2. <cwd>/.claude/checkpoint.md — resume checkpoint with epistemic content

Single pass through transcript extracts both metrics (backward-compatible)
and actual content (new). Content categories:
  - Working summary (last substantial assistant text)
  - Open questions (non-rhetorical "?")
  - Hedged claims (uncertainty language + substance)
  - Negative results (failure/rejection language)
  - Decisions with rationale
  - User corrections (#f prefix)
"""

import json
import os
import re
import subprocess
import sys
from collections import deque
from datetime import datetime

# ─── Sentence splitter ───────────────────────────────────────────────

_SENT_RE = re.compile(r"(?<=[.!?])\s+|\n{2,}")


def sentences(text):
    """Yield non-trivial sentences from a text block."""
    for s in _SENT_RE.split(text):
        s = s.strip()
        if len(s) > 25:
            yield s


# ─── Deduplication ────────────────────────────────────────────────────

def _word_set(s):
    return set(s.lower().split())


def is_near_dup(candidate, existing, threshold=0.6):
    """True if candidate has >threshold Jaccard overlap with any existing."""
    cw = _word_set(candidate)
    if not cw:
        return True
    for e in existing:
        ew = _word_set(e)
        if not ew:
            continue
        jaccard = len(cw & ew) / len(cw | ew)
        if jaccard > threshold:
            return True
    return False


# ─── Classification markers ──────────────────────────────────────────

HEDGING = re.compile(
    r"\b(likely|approximately|suggests?|uncertain|possibly|might|could be|"
    r"unclear|tentative|preliminary|probably|seems|appears to)\b", re.I
)
NEGATIVES = re.compile(
    r"\b(didn.t work|failed|not possible|rejected|can.t|doesn.t work|"
    r"no evidence|won.t work|ruled out|dead end|not feasible|disproved|"
    r"false positive|overstated|false)\b", re.I
)
DECISIONS = re.compile(
    r"\b(decided|chose|because|therefore|the reason|opting for|"
    r"selected|deferred|killed|going with|trade.?off)\b", re.I
)
QUESTIONS_SKIP = re.compile(
    r"\b(right\?|shall I|want me to|does that|sound good|ok\?|ready\?|"
    r"caught your eye|how about|what do you|or just)\b", re.I
)
HEDGING_WORDS = [
    "likely", "approximately", "suggests", "uncertain", "possibly",
    "might", "could", "unclear", "tentative", "preliminary",
]
QUALIFIER_PHRASES = [
    "however", "on the other hand", "caveat",
    "limitation", "exception", "but note",
]
PROVENANCE_TAGS = [
    "[SOURCE:", "[INFERENCE]", "[TRAINING-DATA]", "[PREPRINT]",
    "[FRONTIER]", "[UNVERIFIED]", "[SPEC]", "[CALC]", "[DATA]", "[QUOTE]",
]


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    session = data.get("session_id", "")
    if not session:
        sys.exit(0)

    trigger = data.get("trigger", "unknown")
    cwd = data.get("cwd", "")
    transcript = data.get("transcript_path", "")

    # ─── Extraction state ─────────────────────────────────────────────

    CAP = {"questions": 8, "hedged": 10, "negatives": 6, "decisions": 6}
    buckets = {k: deque(maxlen=v) for k, v in CAP.items()}
    user_corrections = deque(maxlen=5)
    last_substantial_block = ""

    # Metrics (backward-compatible with compact-log.jsonl consumers)
    hedging_count = 0
    qualifier_count = 0
    provenance_tag_count = 0
    assistant_word_count = 0
    t_lines = 0

    # CLIR state
    recent_tools = []
    memory_written = False
    task_context = ""
    task_subjects = []  # all TaskCreate/TaskUpdate subjects

    # Forward-looking state
    last_user_message = ""

    # ─── Single pass through transcript ───────────────────────────────

    if transcript and os.path.isfile(transcript):
        try:
            with open(transcript) as f:
                all_lines = f.readlines()
            t_lines = len(all_lines)

            for raw_line in all_lines:
                try:
                    entry = json.loads(raw_line.strip())
                except Exception:
                    continue

                msg_type = entry.get("type", "")
                content = entry.get("message", {}).get("content", entry.get("content", ""))
                if not isinstance(content, list):
                    continue

                for block in content:
                    if not isinstance(block, dict):
                        continue

                    # ── Tool tracking (CLIR) ──
                    if block.get("type") == "tool_use":
                        name = block.get("name", "")
                        inp = block.get("input", {})
                        if len(recent_tools) < 3 and name:
                            recent_tools.append(name)
                        if name in ("Write", "Edit"):
                            fp = inp.get("file_path", "")
                            if "MEMORY.md" in fp or "/memory/" in fp:
                                memory_written = True
                        if name in ("TaskCreate", "TaskUpdate"):
                            subj = inp.get("subject", inp.get("description", ""))[:120]
                            if subj and not task_context:
                                task_context = subj
                            if subj and subj not in task_subjects:
                                task_subjects.append(subj)

                    # ── Assistant text → metrics + content extraction ──
                    if block.get("type") == "text" and msg_type == "assistant":
                        txt = block.get("text", "")
                        words = txt.split()
                        assistant_word_count += len(words)

                        # Metrics
                        lower = txt.lower()
                        for hw in HEDGING_WORDS:
                            hedging_count += lower.count(hw)
                        for q in QUALIFIER_PHRASES:
                            qualifier_count += lower.count(q)
                        for pt in PROVENANCE_TAGS:
                            provenance_tag_count += txt.count(pt)

                        # Track last substantial block for working summary.
                        # Prefer blocks with epistemic content (hedging, decisions)
                        # over debugging chatter or tool output.
                        if len(words) > 50:
                            has_epistemic = bool(
                                HEDGING.search(txt) or DECISIONS.search(txt)
                                or NEGATIVES.search(txt) or "?" in txt
                            )
                            if has_epistemic or not last_substantial_block:
                                last_substantial_block = txt

                        # Sentence-level extraction
                        for sent in sentences(txt):
                            sw = len(sent.split())

                            if "?" in sent and sw > 8 and not QUESTIONS_SKIP.search(sent):
                                if not is_near_dup(sent, buckets["questions"]):
                                    buckets["questions"].append(sent)
                            elif HEDGING.search(sent) and sw > 8:
                                if not is_near_dup(sent, buckets["hedged"]):
                                    buckets["hedged"].append(sent)
                            elif NEGATIVES.search(sent) and sw > 6:
                                if not is_near_dup(sent, buckets["negatives"]):
                                    buckets["negatives"].append(sent)
                            elif DECISIONS.search(sent) and sw > 8:
                                if not is_near_dup(sent, buckets["decisions"]):
                                    buckets["decisions"].append(sent)

                    # ── User text → last message + corrections ──
                    if block.get("type") == "text" and msg_type == "human":
                        user_txt = block.get("text", "").strip()
                        if user_txt.startswith("#f"):
                            correction = user_txt[2:].strip()[:200]
                            if correction:
                                user_corrections.append(correction)
                        # Track last substantive user message (skip very short ones)
                        if len(user_txt) > 10:
                            last_user_message = user_txt

        except Exception:
            pass  # Entire extraction is best-effort

    # ─── Trim working summary ─────────────────────────────────────────

    if last_substantial_block:
        words = last_substantial_block.split()
        if len(words) > 300:
            last_substantial_block = " ".join(words[-300:])

    # ─── Git state ────────────────────────────────────────────────────

    modified = []
    branch = ""
    recent_commits = ""
    staged = []
    untracked = []
    diff_stat = ""

    if cwd and os.path.isdir(os.path.join(cwd, ".git")):
        def git(*args, timeout=5):
            r = subprocess.run(
                ["git"] + list(args),
                cwd=cwd, capture_output=True, text=True, timeout=timeout
            )
            return r.stdout.strip() if r.returncode == 0 else ""

        try:
            branch = git("rev-parse", "--abbrev-ref", "HEAD")
            modified = [l for l in git("diff", "--name-only").split("\n") if l][:20]
            staged = [l for l in git("diff", "--cached", "--name-only").split("\n") if l][:20]
            untracked = [l for l in git("ls-files", "--others", "--exclude-standard").split("\n") if l][:10]
            recent_commits = git("log", "--oneline", "-5")
            diff_stat = git("diff", "--stat")
        except Exception:
            pass

    # ─── 1. Append to compaction log ──────────────────────────────────

    log_path = os.path.expanduser("~/.claude/compact-log.jsonl")
    log_entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "session": session,
        "trigger": trigger,
        "cwd": cwd,
        "transcript_lines": t_lines,
        "modified_files": modified,
        "clir": {
            "recent_tools": recent_tools,
            "memory_written": memory_written,
            "task_context": task_context,
        },
        "hedging_count": hedging_count,
        "qualifier_count": qualifier_count,
        "provenance_tag_count": provenance_tag_count,
        "assistant_word_count": assistant_word_count,
        "epistemic_items": sum(len(b) for b in buckets.values()),
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(log_entry, separators=(",", ":")) + "\n")

    # ─── 2. Write resume checkpoint ───────────────────────────────────

    if not cwd:
        sys.exit(0)

    checkpoint_dir = os.path.join(cwd, ".claude")
    os.makedirs(checkpoint_dir, exist_ok=True)
    checkpoint_path = os.path.join(checkpoint_dir, "checkpoint.md")

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    has_epistemic = any(buckets.values()) or user_corrections or last_substantial_block

    out = []
    out.append("# Resume Checkpoint")
    out.append("")
    out.append("Written by PreCompact hook at " + ts + ".")
    out.append("This is a handoff document. Prioritize what remains over what happened.")
    out.append("")

    # ── Forward-looking content (FIRST — what to do next) ──

    if last_user_message:
        out.append("## Last Request")
        # Truncate to 300 chars
        msg = last_user_message.replace("\n", " ").strip()
        if len(msg) > 300:
            msg = msg[:297] + "..."
        out.append(msg)
        out.append("")

    if task_subjects:
        out.append("## Pending Tasks")
        for subj in task_subjects:
            out.append("- " + subj)
        out.append("")

    # ── Epistemic content ──

    if has_epistemic:
        out.append("## Epistemic Content")
        out.append("Compaction loses hedging, negative results, and open questions.")
        out.append("These were extracted verbatim from the pre-compaction conversation.")
        out.append("")

        if last_substantial_block:
            out.append("### Working Summary")
            out.append(last_substantial_block.strip())
            out.append("")

        def _fmt(s, maxlen=200):
            s = s.replace("\n", " ").strip()
            return s[:maxlen - 3] + "..." if len(s) > maxlen else s

        if buckets["questions"]:
            out.append("### Open Questions")
            for q in buckets["questions"]:
                out.append("- " + _fmt(q))
            out.append("")

        if buckets["hedged"]:
            out.append("### Hedged Claims (uncertainty preserved)")
            for h in buckets["hedged"]:
                out.append("- " + _fmt(h))
            out.append("")

        if buckets["negatives"]:
            out.append("### Negative Results")
            for n in buckets["negatives"]:
                out.append("- " + _fmt(n))
            out.append("")

        if buckets["decisions"]:
            out.append("### Decisions")
            for d in buckets["decisions"]:
                out.append("- " + _fmt(d))
            out.append("")

        if user_corrections:
            out.append("### User Corrections")
            for c in user_corrections:
                out.append("- " + c)
            out.append("")

    # ── Session state ──

    out.append("## Session State")
    out.append("- **Session:** `" + session + "`")
    out.append("- **Branch:** `" + branch + "`")
    out.append("- **Trigger:** " + trigger)
    out.append("- **Transcript lines:** " + str(t_lines))
    out.append("")

    if recent_tools or task_context:
        out.append("## Pre-Compaction Context")
        if task_context:
            out.append("- **Task:** " + task_context)
        if recent_tools:
            tools_str = ", ".join(recent_tools)
            out.append("- **Last tools:** " + tools_str)
        mem_str = "yes" if memory_written else "no"
        out.append("- **Memory written:** " + mem_str)
        out.append("")

    # ── Git state ──

    if modified or staged:
        out.append("## Uncommitted Changes")
        if staged:
            out.append("### Staged")
            for fn in staged:
                out.append("- `" + fn + "`")
        if modified:
            out.append("### Modified (unstaged)")
            for fn in modified:
                out.append("- `" + fn + "`")
        out.append("")

    if untracked:
        out.append("## New Files (untracked)")
        for fn in untracked:
            out.append("- `" + fn + "`")
        out.append("")

    if diff_stat:
        out.append("## Diff Summary")
        out.append("```")
        out.append(diff_stat)
        out.append("```")
        out.append("")

    if recent_commits:
        out.append("## Recent Commits")
        out.append("```")
        out.append(recent_commits)
        out.append("```")
        out.append("")

    with open(checkpoint_path, "w") as f:
        f.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
