---
name: cards
description: "Use when: writing, refactoring, reviewing or fact-checking flashcards — the operator's Spaced cards (~/cards, formerly Anki), suggestions in his Inbox, generated cards, card ctx/answers/precision, card diagrams. Rules digest (no cloze, one answer, ctx a glance) and the QA loop against Spaced's agent API (lint gate, one-answer/MVA check, suggest-edit, annotations). NOT Spaced app code, or diagrams outside cards (/scientific-drawing)."
user-invocable: true
---

# Cards

The operator reviews his cards in Spaced (`~/Projects/spaced`, collection `~/cards`). This skill is
the short form of his card principles and the QA loop. The full rules, with evidence and examples,
are in `~/Projects/spaced/docs/cards/principles.md`; read the section you need when a case is unclear.

## Rules digest

Spaced's lints enforce the three word limits; the numbers are the defaults in
`~/Projects/spaced/src/lint/config.ts`, and `test/docs/skill-drift.test.ts` there fails if this list
disagrees with them.

- **No cloze.** Q&A cards only; no fill-in-the-blank fronts.
- **One answer (N→1).** Two experts give the same short answer in 6–10 s. A question that allows
  several valid answers (MVA) gets constraints: framework, organism, scope, phase, the answer's
  shape (a number, a name, a mechanism). Otherwise split it.
- **Plain words.** Ask in words he already knows. A technical term appears only as a short gloss in
  ctx: `net +1 charge out per cycle (*electrogenic*)`. Check a term against his deck with
  `rg -i "<term>" ~/cards`.
- **ctx is a glance:** at most 15 words, usually one clause (`ctx-long`; the principles say 5–15).
  If the card fails without its ctx, that content belongs in the question or the answer.
- **ctx connects, never trivia.** It ties the answer to something he already knows: the mechanism,
  why it matters, or the popular belief it corrects. No ctx beats a trivial one. His words on a
  fact fix, 2026-10-14: "ctx is useless ... it's trivia, doesn't help connect".
- **Bold answer:** under 9 words (`answer-long`). Elaboration goes after it or in ctx.
- **Front:** at most 20 words (`front-long`).
- **Avoid binary questions.** Ask for the quantity, the mechanism or the ratio, not X-or-Y or
  yes/no. Keep a binary question only when the comparison itself is the fact, and say why in the
  reason. He accepted one with "i generally don't like binary questions but this one is fine".
- **Numbers carry a precision class** in the attribute block: `.exact`, `.approx`, `.oom`, `.range`
  or `.ineq`, as in `{#k3f9a2 .oom}`. It is for the checks; he never sees it. Never move a visible
  cue ("(range)", "order of magnitude", "Ballpark") out of the question into the class.
- **The question states its setting:** who, where and what was measured, in the question itself,
  not only in ctx, so the fact works from the card's own context. Ask which auditions (US symphony
  orchestras, player behind a screen), not just "per Goldin & Rouse". A citation such as
  `[Goldin & Rouse 2000]` may stay as an optional extra narrowing; it never replaces the setting.
  His words, 2026-10-14: "just make sure there's enough context in the question so that the paper
  is just an extra narrowing", "not me having to remember the exact paper by name". The one-answer
  check reports a miss as `missing-context`.
- **Prefer why-cards.** Ask for the cause or the mechanism. On a fact card, put the one-clause cause
  in ctx: `no nucleus → can't repair`.
- **Cut material is dropped by default.** Text trimmed from ctx becomes its own card only when it is
  a core fact he would want on its own, and at most one per trimmed card. Evidence, 2026-10-14: he
  rejected 4 of 5 spin-offs and kept only the K⁺-leak card, a core fact.
- **Verify facts.** Check every number and claim against a source, including those in the question
  and ctx. The one-answer check tests the cue, not the fact.
- **Hand checks** the panel misses: does the question give the answer away? Does the bold line
  answer the question asked? Does the answer hide two retrieval targets in one sentence?

## QA loop against Spaced

`~/cards` is read-only for agents. Every write goes through the agent API on
`http://127.0.0.1:4100` (or `spaced mcp`), as JSON naming the agent: `{"agent": "<name>", …}`.
Agents propose; he decides.

1. **Read.** `GET /api/agent/source?id=<id>` gives the block exactly as in the deck file, its lints
   and its open threads. `spaced cards --json <id>…` (or `--suggestions open`) gives parsed fields
   and the hash a verdict is filed against.
2. **Draft** the card's full new block in Spaced's Markdown (`docs/FORMAT.md`). Keep `{#id …}` and
   every `![…](media/…)`. A new card has no ID; accepting it assigns one.
3. **Check one answer.** From `~/Projects/spaced`:
   `uv run --project lab python lab/one_answer.py --spaced <id>…`, or
   `--suggestions open --post`, which files each verdict through `POST /api/agent/suggestion-check`.
   `ambiguous`: add constraints. `converges-elsewhere`: the panel agrees on another answer, so fix
   the cue or check the back. `missing-context`: put the setting into the question. Fix once; if
   it still fails, ask him.
4. **File.**
   `POST /api/agent/suggest-edit {agent, reason, edits: [{card, text, kind, why, supersedes?}]}`.
   - `why` (required): one sentence, at most 200 characters, on what changed and why the new text
     is better. He reads it above the diff, so name every change he would otherwise guess at,
     numbers included (2026-10-14: "bigger card refactors should ... have a one sentence explanation
     of why that's better than before"). The server refuses an edit that changes a number when its
     why names none. An open suggestion without one:
     `POST /api/agent/explain {agent, suggestion, why}`.
   - `kind` is `refactor` when the old intervals belong to a different question (accepting resets
     the card's history); otherwise `minor`.
   - The server lints every proposal. It refuses an edit that adds a warning its card lacks, and a
     new card with any warning, naming the rule and the fix. Fix the text. Add
     `lint-ignore=<rule>` only when the lint is wrong for that card, and say why in `reason`.
   - `supersedes: <your open edit of the same card>` withdraws the old one. Never leave two.
   - Tags, the src line and spacing apply without review. Case, punctuation, hyphens, joins,
     typography (Ca2+ → Ca²⁺), small typos and up to three grammar fixes (an article added or
     dropped, is → are, RGCs → RGC) go to a same-meaning judge model, which applies them or leaves
     them for him. Any changed number, sign (− + ~ ↑), unit or symbol case (mV/MV), math or link,
     and any other word added, dropped or replaced, goes to him.
   - New card: `POST /api/agent/suggest {agent, deck, text, reason, why?}`.
5. **Ask him about taste, never about science.** Whether a fact or number is right, whether
   notation is standard, which reading a card means: decide these yourself from sources; don't ask.
   The fix that follows still goes to him as a suggestion, because a rephrasing or a change to what
   a card says is his to take or leave. His words, 2026-10-14: "Science/domain calls are yours", and
   "I do not mean rephreasings or changing semantics". For a taste question (what to learn, wording,
   keep or delete), `POST /api/agent/annotate {agent, card, text}` with one or two sentences that
   name the options. `GET /api/agent/search?awaiting=agent` finds his replies. Act on the reply,
   then `POST /api/agent/annotate/resolve {agent, card, id}`.

Work queues: his flags (`spaced browse --flag BAD`; triage order in `docs/cards/flags.md`),
`DONT_UNDERSTAND` (reword the card in words he knows; unflag once he accepts the fix),
`spaced leeches --json`, and lint hits (`spaced check --lint-only ctx-long,answer-long --json`).
Suspend a card (`POST /api/agent/suspend`) only when it teaches something false.
The full process is `~/Projects/spaced/docs/cards/qa-process.md`.

## Diagrams on cards

A visual earns its place only when its geometry is the concept: blanking on the answer, seeing the
picture brings it back. Bar charts that restate a number fail; historically 6 of 8 candidates did.
Visuals go on the answer side and draw on a small budget (the `media-budget` lint counts them).

| Need | Path |
|---|---|
| Math, 3D, biological structures, circuits, commutative diagrams | TikZ, compiled to PNG |
| Bars, process flows, number lines, thresholds, gradients | Generated or hand-written SVG |
| Small inline molecule glyphs | `lab/diagrams/molecule_svgs.py` |
| Molecule from a SMILES string | RDKit (`uv run --with rdkit`) |

All tools run from `~/Projects/spaced`:

```bash
uv run --project lab python lab/diagrams/tikz.py compile lab/diagrams/sources/<f>.tex --verify
uv run --project lab python lab/diagrams/generate_card_svg.py bar --values "36,32,2" --labels "A,B,C"
uv run --project lab python lab/diagrams/validate_card_svg.py <file.svg | ->
```

SVG colours go in `style="fill:var(--color-highlight)"`, never in `fill=` attributes; the root is
`<svg class="vis" viewBox="0 0 500 105">`. Agents cannot write to `~/cards`: render the file
elsewhere, hand it over to be placed in the deck's `media/`, then file the edit that references it
as `![alt](media/<file>)`. Check the picture for scientific accuracy, not only that it renders.
Details: `references/diagrams.md` (workflow), `references/svg-rules.md`,
`references/domain-tools.md` (chemistry, physics, biology, math packages).

## Pointers

| Need | Where (under `~/Projects/spaced/`) |
|---|---|
| Every rule, failure mode and worked example | `docs/cards/principles.md` |
| QA steps, API calls, verdicts | `docs/cards/qa-process.md` |
| Flags and triage order | `docs/cards/flags.md` |
| Visual design language, SVG patterns | `docs/cards/design-language.md`, `docs/cards/visual-content.md` |
| Math notation (KaTeX) | `docs/cards/math-design-language.md` |
| What makes a cue good, formally | `docs/cards/quality-formalization.md` |
| Image-model bases and occlusion | `docs/cards/image-model-cards.md` |
| Diagram tool survey | `docs/cards/diagram-tools-research.md` |
| Card syntax and attribute block | `docs/FORMAT.md` |
| One-answer check, model routing, diagram tools | `lab/` |
