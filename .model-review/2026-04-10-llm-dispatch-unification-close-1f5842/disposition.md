# Review Findings — 2026-04-10

**5 findings** from 1 axes (0 cross-model agreements)
Structured data: `findings.json`

1. **[HIGH]** Non-functional fallback path in research-ops/scripts/run-cycle.sh
   Category: bug | Confidence: 1.0 | Source: GPT-5.4 (quantitative/formal)
   The script attempts to invoke '$SKILL_DIR/scripts/llm-dispatch.py' when CLAUDE_PROCS exceeds the threshold. However, SKILL_DIR resolves to research-ops/, where no such script exists; the shared wrapper is located at the repo root scripts/llm-dispatch.py. This results in a 100% failure rate for rate-limited cycles.
   File: research-ops/scripts/run-cycle.sh
   Fix: Update the script to resolve the repo root explicitly and call the correct path for llm-dispatch.py.

---

2. **[MEDIUM]** Non-portable direct import interface for shared.llm_dispatch
   Category: architecture | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   Documentation suggests direct Python imports (from shared.llm_dispatch import dispatch) for sibling repos, but there is no mechanism (like packaging or PYTHONPATH management) to make this module available outside of the internal skills repo environment. The current setup only bootstraps sys.path within the wrapper script itself.
   File: improve/SKILL.md
   Fix: Promote shared dispatch to a formal installable package or entrypoint that sibling repos can consume without manual path hacks.

---

3. **[MEDIUM]** Lack of end-to-end integration tests for cross-repo dispatch
   Category: missing | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   There are no automated tests verifying the three primary entry paths for shared-dispatch: overview hook, model-review, and rate-limited research cycle. This leaves the system vulnerable to path drift and contract regressions.
   File: 
   Fix: Add integration tests that shell into research-ops/scripts/run-cycle.sh and other entry points to assert correct path resolution and artifact generation.

---

4. **[LOW]** Policy contradiction between llmx-guide and pretool-llmx-guard
   Category: logic | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   The llmx-guide/SKILL.md documentation states that raw llmx chat is appropriate for debugging, but hooks/pretool-llmx-guard.sh unconditionally blocks these calls in agent Bash environments with no escape hatch for diagnostics.
   File: hooks/pretool-llmx-guard.sh
   Fix: Introduce an explicit, logged debug mode for raw llmx chat or update documentation to reflect a total prohibition.

---

5. **[LOW]** Underutilization of retryability metadata in calling scripts
   Category: performance | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   The shared dispatch helper provides classification for transient failures (timeouts, rate limits), but calling scripts like generate-overview.sh and run-cycle.sh treat all failures as identical, leading to stale artifacts or unnecessary manual intervention.
   File: research-ops/scripts/run-cycle.sh
   Fix: Consume 'retryable' status from dispatch metadata to distinguish transient failures from hard configuration errors and implement retries where appropriate.

---

## Agent Response (fill before implementing)

### Where I disagree with the disposition:
<!-- "Nowhere" is valid. Don't invent disagreements. -->


### Context I had that the models didn't:
<!-- If context file was comprehensive, say so. -->

