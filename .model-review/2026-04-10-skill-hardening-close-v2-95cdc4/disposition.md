# Review Findings — 2026-04-10

**11 findings** from 2 axes (0 cross-model agreements)
Structured data: `findings.json`

1. **[CRITICAL]** `--extract` is documented but rejected by `model-review.py`
   Category: bug | Confidence: 1.0 | Source: Gemini (architecture/patterns)
   The review claims a contract mismatch between documentation and implementation: `review/SKILL.md`, `references/dispatch.md`, and `lenses/adversarial-review.md` instruct users to run `model-review.py` with `--extract`, but the script's `argparse` only exposes `--no-extract`. According to the reviewer, passing `--extract` currently causes an `unrecognized arguments` error and crashes the command.
   File: review/scripts/model-review.py
   Fix: Replace the negative-only flag with `parser.add_argument("--extract", action=argparse.BooleanOptionalAction, default=True)` so both `--extract` and `--no-extract` are accepted, matching the documented CLI.

---

2. **[HIGH]** Path instability in selective manifest linting mode
   Category: bug | Confidence: 1.0 | Source: GPT-5.4 (quantitative/formal)
   The script accepts --manifest as raw Path and prints manifest_path.relative_to(ROOT). A relative path like brainstorm/skill.json is not under absolute ROOT, so relative_to() raises ValueError, crashing the linter.
   File: scripts/lint_skill_manifests.py
   Fix: Normalize all manifest CLI inputs to repo-rooted absolute paths before validation/output by converting each to (ROOT / path).resolve() when relative.

---

3. **[HIGH]** Validator crash on malformed uses.* entries
   Category: bug | Confidence: 1.0 | Source: GPT-5.4 (quantitative/formal)
   The validate_manifest function tests array items for membership (e.g., in PROFILES). Non-string unhashable items like dicts or lists in uses.dispatch_profiles, uses.packet_builders, or uses.artifact_schemas will raise TypeError instead of returning a validation issue.
   File: shared/skill_manifest.py
   Fix: Validate that each array member is a non-empty string before performing membership checks.

---

4. **[MEDIUM]** Custom questions JSON is read without error handling
   Category: bug | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review flags `question_overrides = json.loads(args.questions.read_text())` in `model-review.py` as fragile because it does not catch `JSONDecodeError` for malformed JSON or `FileNotFoundError` if the file disappears after an existence check. The reviewer notes this would surface a raw Python stack trace instead of a controlled CLI error.
   File: review/scripts/model-review.py
   Fix: Wrap the read/parse step in `try/except` for `json.JSONDecodeError` and `FileNotFoundError`, print a descriptive error to `stderr`, and exit with status 1.

---

5. **[MEDIUM]** Review artifacts anchored to process CWD instead of project directory
   Category: logic | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   Review output directories are built using Path('.model-review/...') relative to the process CWD rather than the project directory resolved from --project. This causes artifacts to be written to the wrong tree if the script is invoked from outside the target repository.
   File: review/scripts/model-review.py
   Fix: Anchor review_dir creation to project_dir or add an explicit --output-dir argument.

---

6. **[MEDIUM]** Manifest validator ignores `requires_packet` and `requires_gpt` mode flags used in tests
   Category: missing | Confidence: 0.8 | Source: Gemini (architecture/patterns)
   The review says `scripts/test_skill_manifest.py` includes a mock `skill.json` with `"requires_packet": true` and `"requires_gpt": true` inside `modes`, but `shared/skill_manifest.py` does not validate or acknowledge those fields and only checks `intent_class` and `artifacts`. This is presented as a schema gap between tests and validator behavior.
   File: shared/skill_manifest.py
   Fix: Extend `skill_manifest.py` to explicitly validate `requires_packet` and `requires_gpt` as booleans when present, and consider warning on unknown keys inside `modes`.

---

7. **[MEDIUM]** CLI tests omit the documented `--extract` path
   Category: missing | Confidence: 0.8 | Source: Gemini (architecture/patterns)
   The review identifies a test gap in `test_model_review.py`: it covers `--no-extract` and `--verify` but does not test the documented happy path that invokes the script with `--extract`. The reviewer argues this blind spot is why the CLI contract mismatch was able to slip through.
   File: test_model_review.py
   Fix: Add CLI-level tests that invoke the parser/script with `--extract`, including combinations such as `--extract --verify`, and assert the command does not fail on argument parsing.

---

8. **[MEDIUM]** Brainstorm schema registry underspecifies documented artifact contract
   Category: missing | Confidence: 0.8 | Source: GPT-5.4 (quantitative/formal)
   Registry entries for brainstorm.matrix.v1 and brainstorm.coverage.v1 require fewer fields than documented (missing transfer_mechanism, caller_evidence, etc.), allowing malformed artifacts to pass contract checks.
   File: shared/skill_manifest.py
   Fix: Expand ARTIFACT_SCHEMAS definitions to match the documented matrix/coverage requirements or update documentation to match the registry.

---

9. **[LOW]** JSONL output escapes Unicode despite using UTF-8 file handles
   Category: style | Confidence: 0.9 | Source: Gemini (architecture/patterns)
   The review points out that `observe/scripts/observe_artifacts.py` opens files with `encoding="utf-8"` but serializes records with `json.dumps(..., ensure_ascii=True)`. This forces non-ASCII characters into `\uXXXX` escapes, which the reviewer says defeats the purpose of UTF-8 output, bloats logs, and makes grepping or reading Unicode content harder.
   File: observe/scripts/observe_artifacts.py
   Fix: Change serialization to `json.dumps(record, sort_keys=True, ensure_ascii=False)` when writing UTF-8 JSONL.

---

10. **[LOW]** Contradictory fallback policy in review documentation
   Category: logic | Confidence: 0.9 | Source: GPT-5.4 (quantitative/formal)
   Documentation contains internal contradictions, stating both that models should NEVER be downgraded on failure while also documenting automatic Gemini Pro to Flash fallback behavior.
   File: review/lenses/adversarial-review.md
   Fix: Align the documentation with actual implemented policy: automated fallback is allowed as implemented by the dispatch layer.

---

11. **[LOW]** Prompt documentation embeds Bash subshells that may leak literal control logic to agents
   Category: logic | Confidence: 0.6 | Source: Gemini (architecture/patterns)
   The review warns that `review/references/prompts.md` contains prompt templates with Bash expressions such as `$([ -n "$CONSTITUTION" ] && echo ...)`. If those templates are loaded programmatically as raw prompt text instead of executed in Bash, the control logic would be passed literally into the LLM context rather than expanded.
   File: review/references/prompts.md
   Fix: Rewrite the prompt templates as plain static text or isolate shell-only templating from agent-consumable prompt content so programmatic loaders do not ingest Bash expressions literally.

---

## Agent Response (fill before implementing)

### Where I disagree with the disposition:
<!-- "Nowhere" is valid. Don't invent disagreements. -->


### Context I had that the models didn't:
<!-- If context file was comprehensive, say so. -->

