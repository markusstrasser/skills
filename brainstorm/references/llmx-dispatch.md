<!-- Reference file for brainstorm skill. Loaded on demand. -->
# Shared Dispatch Prompt Payloads

> **Automation path:** use `uv run python3 ~/Projects/skills/scripts/llm-dispatch.py` or the shared Python module in `shared/llm_dispatch.py`.
> This file defines prompt payloads and artifact contracts. It does not teach raw CLI transport use.

All templates assume `$BRAINSTORM_DIR`, `$N_IDEAS`, `$CONSTITUTION`, and `$TOPIC` are set.
If the shared packet builder is available, use its output as `context.md` instead of assembling an ad hoc context blob.
Date injection: `$(date +%Y-%m-%d)` in every system prompt.

## Initial Generation (Step 2)

**With external dispatch (and not `--no-llmx`):** Dispatch to an external model for parallel volume while you also generate your own set.

```bash
cat > "$BRAINSTORM_DIR/external-generation.prompt.md" <<'EOF'
<system>
Generate approaches to the design space below. Maximize breadth — $N_IDEAS genuinely different approaches, not variations on a theme. No feasibility filtering yet. It is $(date +%Y-%m-%d).
</system>

[Design space + constraints + user-provided seeds if any]

For each approach: one paragraph on the mechanism and why it differs from the others.
EOF

uv run python3 ~/Projects/skills/scripts/llm-dispatch.py \
  --profile deep_review \
  --context "$BRAINSTORM_DIR/context.md" \
  --prompt-file "$BRAINSTORM_DIR/external-generation.prompt.md" \
  --output "$BRAINSTORM_DIR/external-generation.md" \
  --meta "$BRAINSTORM_DIR/dispatch.meta.json"
```

Simultaneously, generate your own `$N_IDEAS` approaches. Write to `$BRAINSTORM_DIR/claude-generation.md`.

**Without external dispatch (or `--no-llmx`):** Generate `$N_IDEAS` approaches yourself. Write to `$BRAINSTORM_DIR/initial-generation.md`.

## Artifact Contract

Every brainstorm run should emit these files before synthesis:

- `matrix.json` — canonical row store for ideas, source rounds, axes, domains, paradigms escaped, transfer mechanisms, and dispositions.
- `matrix.md` — rendered coverage matrix for operator review.
- `coverage.json` — aggregate counts, uncovered cells, duplicate/merge counts, and stop reason.
- `extraction.md` — mechanically extracted idea list with source tags.
- `synthesis.md` — ranked disposition after the coverage gate.

If a file cannot be populated, the run is incomplete.

## Denial Cascade (Step 3a)

Default: 2 rounds. `--quick`: 1 round. `--deep`: 3 rounds.

Send the prompt below through the shared dispatch helper. The payload is the contract; the transport is an implementation detail.

```md
<system>
DENIAL ROUND. The approaches below are FORBIDDEN - you cannot use them or their variants. Propose 5 fundamentally different approaches that share no paradigm with the forbidden list. It is $(date +%Y-%m-%d).
</system>

## Forbidden Paradigms
[List 3-5 dominant paradigms from initial generation with brief descriptions]

## Design Space
[Original design space description]

For each: the mechanism, why it differs from ALL forbidden paradigms, one reason it might work.
```

For a second pass, feed the prior denial output back through the same helper with every prior paradigm marked forbidden and request 3+ new approaches. Do not reuse the same transport-specific prompt in the docs; keep the payload stable and let the dispatcher route it.

## Domain Forcing (Step 3b)

If `--domains` specified, use those. Otherwise pick 3 domains **unrelated** to the problem (`--quick`: 2, `--deep`: 4).

```md
<system>
Map a design challenge to three unrelated domains. For each domain: what's the analogous problem, how does that domain solve it, what transfers back. It is $(date +%Y-%m-%d).
</system>

## Design Challenge
[Original design space description]

## Domain 1: [chosen domain]
Analogous problem? How does this domain solve it? What transfers back?

## Domain 2: [chosen domain]
Same.

## Domain 3: [chosen domain]
Same.
```

## Constraint Inversion (Step 3c)

**Skipped in `--quick` mode.** Default: 3 inversions. `--deep`: 4 inversions.

```md
<system>
For each inverted assumption, design the best solution under that altered constraint. Then identify what transfers back to reality. It is $(date +%Y-%m-%d).
</system>

## Design Space
[Original description]

## Inversion 1: [e.g., 'What if compute were free but storage cost $1/byte?']
Best design under this constraint. What transfers back?

## Inversion 2: [e.g., 'What if we had 1000x the data but couldn't iterate?']
Best design. What transfers?

## Inversion 3: [e.g., 'What if this had to work for 50 years without updates?']
Best design. What transfers?
```

## Extraction (Step 4)

```bash
cat "$BRAINSTORM_DIR"/*generation*.md \
    "$BRAINSTORM_DIR"/denial-r*.md \
    "$BRAINSTORM_DIR"/domain-forcing.md \
    "$BRAINSTORM_DIR"/constraint-inversion.md \
    > "$BRAINSTORM_DIR/all-raw.md" 2>/dev/null
```

If shared dispatch is available, send extraction to a fast profile:

```bash
uv run python3 ~/Projects/skills/scripts/llm-dispatch.py \
  --profile fast_extract \
  --context "$BRAINSTORM_DIR/all-raw.md" \
  --prompt "
<system>
Extract every discrete idea, approach, or insight as a numbered list. One per line. Tag the source (initial/denial-r1/denial-r2/domain/constraint), axis, domain row if present, and the matrix cell if available. Do not evaluate - extract mechanically.
</system>

Extract all discrete ideas from the brainstorm artifacts." \
  --output "$BRAINSTORM_DIR/extraction.md"
```

If no shared dispatch is available, extract yourself.

## Matrix Row Contract

`matrix.json` rows should include at least:

- `idea_id`
- `short_name`
- `source_artifact`
- `axis`
- `domain_row`
- `domain`
- `dominant_paradigm_escaped`
- `transfer_mechanism`
- `disposition`
- `merged_into`
- `caller_evidence`
- `speculative`
- `notes`
