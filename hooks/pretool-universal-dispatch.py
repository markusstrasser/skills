#!/usr/bin/env python3
"""pretool-universal-dispatch.py — consolidated PreToolUse catch-all (matcher="").

Merges two formerly-separate hooks that both fired on EVERY tool call, each
re-parsing stdin independently via jq subprocesses:

  1. tool-tracker.sh       — Ghostty tab-title state + duplicate-read detection
                              (can BLOCK via exit 2 at >=4 full-file reads).
  2. pretool-companion-remind.sh — advisory skill-load reminders (always exit 0).

This dispatcher reads stdin ONCE and runs both jobs in-process. Behavioral
parity with the two originals is the contract — see
skills/hooks/test_universal_dispatch.py. The originals are left on disk
un-wired as a rollback fallback; do not delete them here.

Fail-open: any unexpected internal error exits 0 rather than blocking a tool
call. The ONLY intentional non-zero exit is the dup-read >=4 block (exit 2),
mirroring tool-tracker.sh exactly.
"""

import json
import os
import re
import subprocess
import sys
import time

HOME = os.path.expanduser("~")
SKILLS_HOOKS = "/Users/alien/Projects/skills/hooks"

# State-dir override for hermetic testing only. Unset in production (default
# "/tmp"), matching both originals' hardcoded /tmp/claude-*-$PPID paths
# exactly — this env var does not exist in either original and changes
# nothing when unset.
STATE_DIR = os.environ.get("CLAUDE_HOOK_STATE_DIR", "/tmp")


# ---------------------------------------------------------------------------
# Shared stdin parse (was ~18 separate jq subprocess calls across both hooks)
# ---------------------------------------------------------------------------


def load_envelope():
    raw = sys.stdin.read()
    try:
        envelope = json.loads(raw) if raw.strip() else {}
    except Exception:
        envelope = {}
    if not isinstance(envelope, dict):
        envelope = {}

    tool_name = envelope.get("tool_name") or ""
    if not tool_name or tool_name == "null":
        tool_name = os.environ.get("CLAUDE_TOOL_NAME", "unknown")

    tool_input = envelope.get("tool_input")
    if not isinstance(tool_input, dict):
        # Fallback path parity with tool-tracker.sh's CLAUDE_TOOL_INPUT env
        # var. Per MEMORY.md hook-input-contract, Claude never sets
        # CLAUDE_TOOL_* env vars in practice (stdin envelope only) — this is
        # dead-code parity, not a live path.
        env_input = os.environ.get("CLAUDE_TOOL_INPUT", "")
        try:
            tool_input = json.loads(env_input) if env_input else {}
        except Exception:
            tool_input = {}
        if not isinstance(tool_input, dict):
            tool_input = {}

    return envelope, tool_name, tool_input


def field(tool_input, envelope, *keys):
    """First non-empty value across tool_input then top-level envelope, per key in order."""
    for key in keys:
        v = tool_input.get(key)
        if v not in (None, ""):
            return v
    for key in keys:
        v = envelope.get(key)
        if v not in (None, ""):
            return v
    return ""


# ---------------------------------------------------------------------------
# Part 1 — tab-title + duplicate-read tracking (tool-tracker.sh port)
# ---------------------------------------------------------------------------


def run_tab_and_dupread(tool_name, tool_input, ppid):
    """Returns (warn_text_or_None, block_bool)."""
    # --- action string (Ghostty tab title) ---
    if tool_name in ("Read", "Write", "Edit"):
        fp = tool_input.get("file_path") or ""
        target = os.path.basename(fp) if fp else ""
        action = f"{tool_name} {target}"
    elif tool_name == "Bash":
        cmd = (tool_input.get("command") or "")[:25]
        action = f"$ {cmd}"
    elif tool_name == "Grep":
        pat = (tool_input.get("pattern") or "")[:15]
        action = f"Grep {pat}"
    elif tool_name == "Glob":
        pat = (tool_input.get("pattern") or "")[:15]
        action = f"Glob {pat}"
    elif tool_name == "Agent":
        desc = (tool_input.get("description") or "")[:20]
        action = f"Agent: {desc}"
    elif tool_name.startswith("mcp__"):
        short = tool_name
        short = short.replace("mcp__", "", 1)
        short = short.replace("__", ":")
        if short.endswith("_exa"):
            short = short[: -len("_exa")]
        short = short.replace("web_search", "search", 1)
        action = short[:15]
    else:
        action = tool_name

    # --- reset agent-cascade counter on non-Agent tools ---
    if tool_name != "Agent":
        try:
            with open(f"{STATE_DIR}/claude-non-agent-{ppid}", "w") as f:
                f.write(str(int(time.time())))
        except OSError:
            pass

    # --- duplicate-read detection ---
    reads_file = f"{STATE_DIR}/claude-reads-{ppid}"
    counter_file = f"{STATE_DIR}/claude-toolcount-{ppid}"
    recency_window = 20

    try:
        tool_count = int(open(counter_file).read().strip())
    except Exception:
        tool_count = 0
    tool_count += 1
    try:
        with open(counter_file, "w") as f:
            f.write(str(tool_count))
    except OSError:
        pass

    warn = None
    block = False
    fpath = ""
    total_reads = 1

    if tool_name == "Read":
        fpath = tool_input.get("file_path") or ""
        offset = tool_input.get("offset")
        has_offset = offset not in (None, "")
        dedup_key = fpath
        if fpath and os.path.isfile(reads_file):
            dedup_key = f"{fpath}@{offset}" if has_offset else fpath
            lines = []
            try:
                with open(reads_file) as f:
                    lines = f.read().splitlines()
            except OSError:
                lines = []

            # TOTAL_READS: exact match on first field (grep -cxF) — only
            # full-file reads (no offset) count.
            total_reads = sum(1 for ln in lines if ln.split("|", 1)[0] == fpath)

            if not has_offset and total_reads >= 4:
                warn = (
                    f"BLOCKED: {os.path.basename(fpath)} read {total_reads}x this session "
                    "(full file). Content is in context. Use offset/limit for a specific "
                    "section, or explain why you need the full content again."
                )
                block = True
            elif not has_offset and total_reads >= 3:
                warn = (
                    f"REPEATED READ ({total_reads}x): {os.path.basename(fpath)} — content is "
                    "likely still in context. Use offset/limit if you need a specific section."
                )
            else:
                # recency-window check on the same dedup_key (last match wins)
                prev_count = None
                for ln in lines:
                    parts = ln.split("|", 1)
                    if len(parts) == 2 and parts[0] == dedup_key:
                        try:
                            prev_count = int(parts[1])
                        except ValueError:
                            prev_count = None
                if prev_count is not None and (tool_count - prev_count) < recency_window:
                    warn = (
                        f"DUPLICATE READ: {os.path.basename(fpath)} was read "
                        f"{tool_count - prev_count} tool calls ago. The content is likely "
                        "still in context."
                    )
        if fpath:
            try:
                with open(reads_file, "a") as f:
                    f.write(f"{dedup_key}|{tool_count}\n")
            except OSError:
                pass

    elif tool_name in ("Write", "Edit"):
        fpath = tool_input.get("file_path") or ""
        if fpath and os.path.isfile(reads_file):
            try:
                with open(reads_file) as f:
                    lines = f.read().splitlines()
                # Bug-compatible with original `grep -vF "$fpath"`: substring
                # match anywhere in the line, not exact first-field match.
                kept = [ln for ln in lines if fpath not in ln]
                with open(reads_file, "w") as f:
                    f.write("\n".join(kept) + ("\n" if kept else ""))
            except OSError:
                pass

    try:
        with open(f"{STATE_DIR}/claude-tab-tool-{ppid}", "w") as f:
            f.write(action)
    except OSError:
        pass

    if warn:
        level = "block" if block else "warn"
        try:
            subprocess.run(
                [f"{SKILLS_HOOKS}/hook-trigger-log.sh", "dup-read", level, os.path.basename(fpath)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
        except Exception:
            pass

        print(json.dumps({"additionalContext": warn}))

        shadow_log = os.path.join(HOME, ".claude", "dup-read-shadow.jsonl")
        try:
            with open(shadow_log, "a") as f:
                f.write(
                    json.dumps(
                        {
                            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            "file": os.path.basename(fpath),
                            "reads": total_reads,
                            "ppid": str(ppid),
                            "blocked": block,
                        }
                    )
                    + "\n"
                )
        except OSError:
            pass

    return warn, block


# ---------------------------------------------------------------------------
# Part 2 — companion skill-load reminders (pretool-companion-remind.sh port)
# ---------------------------------------------------------------------------

SEARCH_TOOL_RE = re.compile(
    r"mcp__exa|mcp__research|mcp__paper-search|mcp__brave-search|mcp__firecrawl|"
    r"mcp__perplexity|WebSearch|WebFetch"
)


def run_companion_remind(envelope, tool_name, tool_input):
    session_id = os.environ.get("CLAUDE_SESSION_ID", "default")
    reminder_dir = f"{STATE_DIR}/companion-remind-{session_id}"
    counter_dir = os.path.join(reminder_dir, "counters")
    os.makedirs(reminder_dir, exist_ok=True)
    os.makedirs(counter_dir, exist_ok=True)

    def already_reminded(skill):
        return os.path.isfile(os.path.join(reminder_dir, skill))

    def mark_reminded(skill):
        try:
            open(os.path.join(reminder_dir, skill), "a").close()
        except OSError:
            pass

    def remind(skill, msg):
        if not already_reminded(skill):
            mark_reminded(skill)
            print(f"[companion] {msg}", file=sys.stderr)

    def increment_counter(name):
        path = os.path.join(counter_dir, name)
        try:
            count = int(open(path).read().strip())
        except Exception:
            count = 0
        count += 1
        try:
            with open(path, "w") as f:
                f.write(str(count))
        except OSError:
            pass
        return count

    cmd = ""
    query = ""
    fpath = ""
    content = ""
    is_search_tool = False

    if tool_name == "Bash":
        cmd = field(tool_input, envelope, "command")
    elif SEARCH_TOOL_RE.search(tool_name):
        is_search_tool = True
        q = field(tool_input, envelope, "query", "search_query", "prompt", "url", "claim")
        query = (q or "").lower()
    elif tool_name in ("Write", "Edit"):
        fpath = field(tool_input, envelope, "file_path")
        c = field(tool_input, envelope, "content", "new_string")
        content = (c or "")[:2000]

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")

    # --- counter-based: search API burst -> research skill ---
    if is_search_tool:
        search_count = increment_counter("search-api")
        if search_count == 3:
            remind(
                "research",
                "3+ search API calls this session. Load the research skill (/research) for "
                "routing guidance: S2 for literature (free, structured), Exa for semantic "
                "discovery, Brave for triangulation, verify_claim for spot-checks. Axis "
                "diversity and phase separation prevent shallow convergence.",
            )

    # =========================== HIGH-VALUE ===========================

    # llmx-guide: Bash calls llmx (case-sensitive substring)
    if cmd and "llmx" in cmd:
        if re.search(
            r"anthropic-direct|claude-opus|claude-fable|claude-cli|-p anthropic", cmd, re.I
        ):
            remind(
                "llmx-guide",
                "Claude via llmx: use --subscription (NEVER anthropic-direct/API by default). "
                "Load llmx-guide for flags and gotchas.",
            )
        else:
            remind(
                "llmx-guide",
                "You're calling llmx. Load the llmx-guide skill if you haven't — it has valid "
                "model names, flags, and gotchas.",
            )

    # llmx-guide: Python code dispatching to CLI models (case-sensitive)
    if content and re.search(
        r"subprocess.*(llmx|codex|gemini )|Popen.*(llmx|codex|gemini )", content
    ):
        remind(
            "llmx-guide",
            "Code dispatches to CLI models. Load llmx-guide for subprocess gotchas (shell=True "
            "breaks on parens, output capture, timeouts).",
        )

    # epistemics: bio/medical search terms (case-insensitive)
    if query and re.search(
        r"biotech|antiaging|anti-aging|neuroscience|genomic|pharmacogen|supplement|longevity|"
        r"clinical.trial|drug.target|gene.therapy|CRISPR|mRNA|peptide|nootropic|senolytic|"
        r"rapamycin|metformin|NAD\+?|telomere|mitochondri|epigenetic|proteom|metabolom|"
        r"microbiome|statin|GLP.?1|semaglutide|autophagy|senescen|oxidative.stress|"
        r"inflammation.*marker|blood.brain.barrier",
        query,
        re.I,
    ):
        remind(
            "epistemics",
            "Bio/medical research detected. Read ~/Projects/skills/references/epistemics/"
            "SKILL.md for evidence hierarchy and anti-hallucination rules for health claims.",
        )

    # entity-management: query ticker/entity terms (case-sensitive, matched against already-lowered query — bug-compatible with original)
    if query and re.search(
        r"\b(ticker|stock|equity|company|CEO|founder|executive|board.member)\b", query
    ):
        remind(
            "entity-management",
            "Entity-related search detected. Use /entity-management to create/update structured "
            "entity files instead of ad-hoc notes.",
        )
    # entity-management: file path (case-insensitive)
    if fpath and re.search(r"entities/|dossier|profile", fpath, re.I):
        remind(
            "entity-management",
            "Writing to entity path. Load entity-management skill for schema and versioning "
            "conventions.",
        )

    # modal: Bash command (case-sensitive)
    if cmd and re.search(
        r"\bmodal\b.*deploy|\bmodal\b.*run|\bmodal\b.*serve|from modal import|import modal", cmd
    ):
        remind(
            "modal",
            "Modal CLI/code detected. Load the modal skill for API gotchas, GPU configs, and "
            "v1.0-1.3.x patterns.",
        )
    # modal: content (case-sensitive)
    if content and re.search(
        r"from modal import|import modal|@modal\.(function|cls|method)|modal\.App|modal\.Image|"
        r"modal\.Volume",
        content,
    ):
        remind(
            "modal",
            "Modal code detected. Load the modal skill for API gotchas, GPU configs, and "
            "v1.0-1.3.x patterns.",
        )

    # skill-authoring: writing a SKILL.md (case-sensitive)
    if fpath and re.search(r"SKILL\.md$", fpath):
        remind(
            "skill-authoring",
            "Writing a SKILL.md. Load skill-authoring for frontmatter validation, progressive "
            "disclosure, and scope-check conventions.",
        )

    # source-grading: SQL in intel context
    if (
        cmd
        and re.search(r"duckdb|\.sql|SELECT.*FROM.*WHERE", cmd, re.I)
        and re.search(r"intel", project_dir, re.I)
    ):
        remind(
            "source-grading",
            "SQL query in intel context. Read ~/Projects/skills/references/source-grading/"
            "SKILL.md for data provenance — NATO Admiralty grades on source reliability.",
        )

    # perplexity demotion (case-sensitive)
    if re.search(r"perplexity_search|perplexity_ask", tool_name):
        remind(
            "perplexity-demoted",
            "perplexity_search/ask are demoted (5x Exa cost). Use Exa or Brave for breadth "
            "queries. Reserve perplexity_reason (complex why) and perplexity_research (deep "
            "survey) for decisive use only.",
        )

    # s2-for-papers nudge
    if query and re.search(r"mcp__exa|mcp__brave|WebSearch", tool_name):
        if re.search(
            r"paper|arxiv|preprint|et al\.?|icml|neurips|emnlp|acl |iclr|cvpr|aaai|naacl|colm |iccv",
            query,
            re.I,
        ):
            remind(
                "s2-for-papers",
                "Paper/venue name detected in web search. Use S2 (search_papers) first — free, "
                "structured metadata, citation counts, zero hallucinated citations. Fall back "
                "to Exa only if S2 misses.",
            )

    # verify_claim: intel entity/research writes
    if fpath and re.search(r"intel", project_dir, re.I):
        if re.search(r"entities/|docs/research/|analysis/", fpath, re.I):
            remind(
                "verify-claims-intel",
                "Writing intel research/entity file. Use verify_claim to spot-check key "
                "financial claims (~$0.005/call, cached 7d). Cheap insurance against "
                "hallucinated numbers.",
            )

    # ========================= MEDIUM-VALUE =========================

    # analyze causal
    if query and re.search(
        r"why (does|did|do|is|are|was|were|has|have|would|could)\b.*\b(cause|effect|impact|lead|"
        r"result|driven|because|correlation|associate)",
        query,
        re.I,
    ):
        remind(
            "analyze-causal",
            "Causal 'why' question detected in search. Consider /analyze causal to enforce "
            "explanatory specificity and prevent factor-listing.",
        )

    # analyze dag + robustness: regression in code (case-sensitive)
    if content and re.search(
        r"statsmodels.*OLS|LinearRegression|sm\.OLS|lm\(.*~|regression_results|"
        r"\.fit\(\).*summary|causal_effect|treatment_effect|ATE\b|ATT\b",
        content,
    ):
        remind(
            "analyze-dag",
            "Regression/causal estimation in code. Use /analyze dag to validate DAG structure "
            "and adjustment sets before fitting. Follow with /analyze robustness for "
            "sensitivity analysis.",
        )
    if cmd and re.search(r"statsmodels|causal|regression.*ols|dowhy", cmd):
        remind(
            "analyze-dag",
            "Causal/regression analysis detected. Use /analyze dag for DAG validation and "
            "/analyze robustness for sensitivity (PySensemakr).",
        )

    # analyze hypotheses
    if query and re.search(
        r"(fraud.*(error|mistake|legitimate)|bug.*(design|feature|intentional)|"
        r"alternative.*(explanation|hypothesis|theor)|competing.*(hypothesis|explanation)|"
        r"root.cause.*(analysis|investigation)|differential.diagnosis)",
        query,
        re.I,
    ):
        remind(
            "analyze-hypotheses",
            "Multiple competing explanations detected. Use /analyze hypotheses (ACH) for "
            "structured Bayesian analysis instead of narrative comparison.",
        )

    # data-acquisition: scraping (case-sensitive)
    if cmd and re.search(
        r"curl_cffi|scrapfly|playwright|browserbase|selenium|requests\.get.*html|beautifulsoup|scrapy",
        cmd,
    ):
        remind(
            "data-acquisition",
            "Web scraping code detected. Read ~/Projects/skills/references/data-acquisition/"
            "SKILL.md for tool selection matrix, fallback chains, and macOS-specific gotchas.",
        )
    if content and re.search(
        r"from curl_cffi|from scrapfly|from playwright|from browserbase|import scrapy|"
        r"BeautifulSoup|httpx.*scrape",
        content,
    ):
        remind(
            "data-acquisition",
            "Web scraping imports detected. Read ~/Projects/skills/references/data-acquisition/"
            "SKILL.md for tool selection, API keys, and authenticated session approaches.",
        )

    # analyze investigate
    if query and re.search(
        r"shell.company|beneficial.owner|money.laundering|audit.trail|follow.the.money|OSINT|"
        r"due.diligence|corporate.registry|UBO|sanctions.screen|related.party|insider.trading|"
        r"SEC.filing.*fraud|whistleblow",
        query,
        re.I,
    ):
        remind(
            "analyze-investigate",
            "Forensic/OSINT investigation pattern detected. Use /analyze investigate for "
            "adversarial methodology and cross-domain techniques.",
        )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main():
    block = False
    try:
        envelope, tool_name, tool_input = load_envelope()
        ppid = os.getppid()

        # Reap stale per-PPID trackers. Nothing reaped them before: 312,368 had piled up
        # in /tmp, and genomics' staged_ownership_guard globs that dir 4x per commit, so
        # every commit paid ~5.6s. Throttled to one scan per 10 min, so the hot-path cost
        # here is a single stat(). Never raises. See reap_stale_trackers.py.
        try:
            _hook_dir = os.path.dirname(os.path.abspath(__file__))
            if _hook_dir not in sys.path:
                sys.path.insert(0, _hook_dir)
            from reap_stale_trackers import maybe_reap

            maybe_reap(STATE_DIR)
        except Exception:
            pass

        # Companion reminders first (advisory, stderr-only, never blocks).
        run_companion_remind(envelope, tool_name, tool_input)

        # Tab-title + dup-read tracking (may set block=True; prints stdout JSON itself).
        block = run_tab_and_dupread(tool_name, tool_input, ppid)[1]
    except Exception:
        # Fail-open: never let an internal error block a tool call.
        sys.exit(0)

    sys.exit(2 if block else 0)


if __name__ == "__main__":
    main()
