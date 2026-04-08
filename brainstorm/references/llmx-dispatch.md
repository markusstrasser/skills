<!-- Reference file for brainstorm skill. Loaded on demand. -->
# llmx Dispatch Templates

> **DISPATCH VIA PYTHON API, NOT CLI.** Use `from llmx.api import chat as llmx_chat` and call
> `llmx_chat(prompt=..., provider=..., model=..., timeout=...)`. Read context files with
> `Path(...).read_text()` and write outputs with `Path(...).write_text(response.content)`.
> The CLI commands below are template references for the prompt content — adapt them to Python API calls.
> Bootstrap: `sys.path.insert(0, glob.glob(str(Path.home() / ".local/share/uv/tools/llmx/lib/python*/site-packages"))[0])`

All templates assume `$BRAINSTORM_DIR`, `$N_IDEAS`, `$CONSTITUTION`, and `$TOPIC` are set.
Date injection: `$(date +%Y-%m-%d)` in every system prompt.

## Initial Generation (Step 2)

**With llmx (and not `--no-llmx`):** Dispatch to an external model for parallel volume while you also generate your own set.

```bash
llmx chat -m gemini-3.1-pro-preview \
  ${CONSTITUTION:+-f "$BRAINSTORM_DIR/context.md"} \
  --max-tokens 65536 --timeout 300 \
  -o "$BRAINSTORM_DIR/external-generation.md" "
<system>
Generate approaches to the design space below. Maximize breadth — $N_IDEAS genuinely different approaches, not variations on a theme. No feasibility filtering yet. It is $(date +%Y-%m-%d).
</system>

[Design space + constraints + user-provided seeds if any]

For each approach: one paragraph on the mechanism and why it differs from the others."
```

Simultaneously, generate your own `$N_IDEAS` approaches. Write to `$BRAINSTORM_DIR/claude-generation.md`.

**Without llmx (or `--no-llmx`):** Generate `$N_IDEAS` approaches yourself. Write to `$BRAINSTORM_DIR/initial-generation.md`.

## Denial Cascade (Step 3a)

Default: 2 rounds. `--quick`: 1 round. `--deep`: 3 rounds.

```bash
# Round 1
llmx chat -m gemini-3.1-pro-preview \
  --max-tokens 65536 --timeout 300 \
  -o "$BRAINSTORM_DIR/denial-r1.md" "
<system>
DENIAL ROUND. The approaches below are FORBIDDEN — you cannot use them or their variants. Propose 5 fundamentally different approaches that share no paradigm with the forbidden list. It is $(date +%Y-%m-%d).
</system>

## Forbidden Paradigms
[List 3-5 dominant paradigms from initial generation with brief descriptions]

## Design Space
[Original design space description]

For each: the mechanism, why it differs from ALL forbidden paradigms, one reason it might work."
```

```bash
# Round 2
llmx chat -m gemini-3.1-pro-preview \
  -f "$BRAINSTORM_DIR/denial-r1.md" \
  --max-tokens 65536 --timeout 300 \
  -o "$BRAINSTORM_DIR/denial-r2.md" "
<system>
DENIAL ROUND 2. Everything above is now ALSO forbidden. Go deeper — what paradigm hasn't been touched at all? What would someone from a completely unrelated field propose? 3+ approaches. It is $(date +%Y-%m-%d).
</system>

## Also Forbidden Now
[Paradigms from Round 1]

3+ approaches sharing no paradigm with anything above."
```

## Domain Forcing (Step 3b)

If `--domains` specified, use those. Otherwise pick 3 domains **unrelated** to the problem (`--quick`: 2, `--deep`: 4).

```bash
llmx chat -m gpt-5.4 \
  --reasoning-effort medium --stream --timeout 600 \
  -o "$BRAINSTORM_DIR/domain-forcing.md" "
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
Same."
```

## Constraint Inversion (Step 3c)

**Skipped in `--quick` mode.** Default: 3 inversions. `--deep`: 4 inversions.

```bash
llmx chat -m gpt-5.4 \
  --reasoning-effort medium --stream --timeout 600 \
  -o "$BRAINSTORM_DIR/constraint-inversion.md" "
<system>
For each inverted assumption, design the best solution under that altered constraint. Then identify what transfers back to reality. It is $(date +%Y-%m-%d).
</system>

## Design Space
[Original description]

## Inversion 1: [e.g., 'What if compute were free but storage cost \$1/byte?']
Best design under this constraint. What transfers back?

## Inversion 2: [e.g., 'What if we had 1000x the data but couldn't iterate?']
Best design. What transfers?

## Inversion 3: [e.g., 'What if this had to work for 50 years without updates?']
Best design. What transfers?"
```

## Extraction (Step 4)

```bash
cat "$BRAINSTORM_DIR"/*generation*.md \
    "$BRAINSTORM_DIR"/denial-r*.md \
    "$BRAINSTORM_DIR"/domain-forcing.md \
    "$BRAINSTORM_DIR"/constraint-inversion.md \
    > "$BRAINSTORM_DIR/all-raw.md" 2>/dev/null
```

If llmx available, dispatch extraction to a fast model:

```bash
llmx chat -m gemini-3-flash-preview --timeout 120 \
  -f "$BRAINSTORM_DIR/all-raw.md" \
  -o "$BRAINSTORM_DIR/extraction.md" "
<system>
Extract every discrete idea, approach, or insight as a numbered list. One per line. Tag the source (initial/denial-r1/denial-r2/domain/constraint). Do not evaluate — extract mechanically.
</system>

Extract all discrete ideas from the brainstorm artifacts."
```

If no llmx, extract yourself.
