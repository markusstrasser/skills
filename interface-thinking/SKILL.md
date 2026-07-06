---
name: interface-thinking
description: "Use when: designing/critiquing any interface, tool, UI, feedback loop, or agent-facing representation/cockpit/instrument; 'how should this feel', 'why is this clunky'. Victor/Norman/Engelbart lenses. NOT visual styling or ideation."
user-invocable: true
argument-hint: "[lens] [the interface/tool/loop to think about]"
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit]
effort: high
---

# Interface Thinking

A reasoning-lens library for designing and critiquing **any** interface — a GUI, a CLI, an editor,
an API, a debugger, an agent's tool surface, a document. It does not produce visual styling
(that's `/frontend-design`) and it is not divergent ideation (`/brainstorm`). It gives you a small
set of sharp questions that the people who thought hardest about this — Bret Victor, Don Norman,
Doug Engelbart, Andy Matuschak, Edward Tufte, Ivan Sutherland — keep returning to.

The core conviction behind every lens: **an interface is a machine for closing the distance between
a person's intent and the world's response.** Everything else is decoration.

## Step 0 — Ground in the discipline BEFORE the lenses (do this first, always)

The lenses below are a *thinking* layer. They are NOT a substitute for the field. Before applying
them to any real artifact:

1. **Name the discipline and the product category** the artifact lives in. "Improve the editor" is
   not a Bret-Victor question — it's an **HCI/UX** question about a **timeline/animation editor** and
   an **inspection/debugging tool**. The named thinkers you happen to know are a *subset*, not the
   field.
2. **Pull the canonical heuristics of that discipline** (the §Reference HCI canon below: Nielsen 10,
   Shneiderman 8, Fitts/Hick/Miller, Gestalt) AND **the conventions of that product category** (the
   §Domain pattern libraries below). Search for them if not in hand — the canon is stable and cheap
   to verify.
3. **Then** run the lenses, *applying* the canon and category conventions — don't re-derive from
   scratch what the field already settled. A feature you're about to invent usually has a name, a
   convention, and a known failure mode in the literature (e.g. "ghost trail" = **onion skinning**,
   with a cyan-past / magenta-future color convention).

The failure this step exists to prevent: **scoping research to the named entities in the prompt and
designing from them, when the actual task is governed by a whole discipline you never went and got.**
If improving a surface is part of the project (and editor/tooling work usually is), researching its
governing field and applying it is not optional and not something to wait to be told. See the
research skill's "research the governing discipline, not just the named sub-topic."

## How to use

Pick the lens that matches the symptom, or run the **default sweep** (all seven, fast) for a full
critique. For each lens: state the gap it exposes *in this specific interface*, then the concrete
move that closes it. Output a short findings list — gap → fix → which principle — not an essay.

```
/interface-thinking                     # default sweep over the interface in context
/interface-thinking gulfs <thing>       # just the execution/evaluation gaps
/interface-thinking directness <thing>  # just the feedback-loop latency
/interface-thinking ladder <thing>      # concrete↔abstract / one-vs-all
```

## The Seven Lenses

### 1. `gulfs` — Norman's two gaps
Every interaction has a **gulf of execution** (how do I express what I want?) and a **gulf of
evaluation** (how do I tell if it worked / what state I'm in now?). Ask:
- To do the most common action, how many steps / how much translation from intent to input?
- After an action, can the user see the result *and confirm it matched intent* without extra work?
- Are **affordances** (what's possible) and **signifiers** (how you'd know) present, or is it a
  guessing game? Most "clunky" complaints are an un-narrowed gulf — find which of the two it is.

### 2. `directness` — Victor's immediate connection
Collapse the latency between an action and its visible effect toward zero.
- Count the gaps in the loop. `edit → save → compile → run → look` is **four** gaps. How many here?
- Can the user **grab the thing itself** and change it, or must they edit a distant representation
  (a number in code, a config) and infer the effect?
- Is there a **dead representation** where a live one belongs (a static value where a draggable
  one, a sparkline, or a scrubber would show behavior)?

### 3. `hidden-state` — Victor's "show the data"
If understanding the current state requires replaying history in your head, the representation failed.
- What state is **invisible** right now and has to be held in working memory or reconstructed?
- Is the user shown **the data**, or only the code/process that produces it? Show the data.
- Where does **flow over time** hide behind a single instantaneous view?

### 4. `ladder` — Victor's ladder of abstraction (+ Tufte's small multiples)
Understanding lives in moving between *one concrete instance* and *all instances at once*.
- Can the user see a **single concrete case** (this frame, this row, this run) AND the **whole
  space/trajectory** (all frames, the distribution, every run) — and switch fluidly?
- Is there a place a **small-multiples / filmstrip / overlay** view would replace mental simulation?
- Is the user stuck at one rung (only the concrete, or only the abstract summary)?

### 5. `constraints` — Sutherland's direct-manipulation-with-relationships
Let the user grab the thing; let the system maintain what they declared.
- Are relationships the user cares about **declared and maintained**, or re-enforced by hand each edit?
- When a constraint can't hold, is the **residual/violation visible**, or does it fail silently?
- Can the user manipulate directly *and* trust invariants won't break? (Both, or it's not a tool.)

### 6. `ceiling` — Engelbart's bicycle, not a tricycle
"Easy" is not the only goal. Optimize the **expert's** loop; accept a learning curve for power.
- Does this raise the **ceiling** (what a skilled user can achieve) or only lower the **floor**
  (first five minutes)? Name which.
- Is power being sanded off to flatter novices? Is there a **co-evolution** path — does the user get
  more capable *with* the tool over time, or stay a permanent beginner?
- Beware "intuitive" as the sole metric: the most powerful instruments are learned, not guessed.

### 7. `cognition` — Matuschak's medium-as-memory
The tool's job isn't done when it *displays*; it's done when the user **understands and retains**.
- Does the interface have a **model of what the user has seen / verified / understood**, or does it
  display once and forget?
- Does it **resurface and link** knowledge (this connects to that), or dump a transcript?
- For a review/inspection tool: can the user leave **durable annotations** tied to the thing, that
  come back when relevant? "Notes should surprise you."

## Default sweep procedure
1. Name the interface and its **single most common action** (the hot path).
2. Run lenses 1→7, one line each: *gap in THIS interface → concrete fix → principle*.
3. Rank fixes by (loop-frequency × gap-size). The hot path's gulf beats a rare feature's polish.
4. Flag the **ceiling vs floor** tension explicitly if any fix trades one for the other — that's a
   taste/telos call for the human, not a default.
5. Output: a findings table, not prose. Each row actionable.

## Anti-patterns this skill exists to break
- **Styling-as-design** — reaching for color/spacing/animation when the problem is an un-narrowed
  gulf or a dead representation. Fix the loop before the paint.
- **Novice-only optimization** — measuring only "is it intuitive in 5 minutes" and silently
  capping the ceiling.
- **Display-and-forget** — assuming that showing information means the user understood it (Matuschak's
  "why books don't work").
- **Mental-simulation tax** — making the user replay history or imagine the trajectory because the
  tool only shows one instant.
- **Invisible failure** — a constraint/relationship that breaks silently instead of surfacing its
  residual.

## Reference: the HCI canon (the lenses' empirical backing)

The seven lenses are a synthesis; these are the field's load-bearing checklists. Apply them directly.

- **Nielsen's 10 usability heuristics** (1994, NN/G — for *auditing* an existing UI): 1 visibility of
  system status · 2 match system↔real world · 3 user control & freedom (undo/redo, exits) · 4
  consistency & standards · 5 error prevention · 6 **recognition rather than recall** (show options,
  don't make users remember) · 7 **flexibility & efficiency** (accelerators/shortcuts for experts) ·
  8 aesthetic & minimalist design · 9 help users recognize/diagnose/recover from errors · 10 help &
  documentation.
- **Shneiderman's 8 golden rules** (1986/2016, cs.umd.edu/~ben — for *designing* a new UI): 1 strive
  for consistency · 2 seek universal usability (novice AND expert) · 3 offer informative feedback · 4
  design dialogs to yield closure · 5 prevent errors · 6 **permit easy reversal of actions** · 7 keep
  users in control (internal locus of control) · 8 reduce short-term memory load.
- **Quantitative laws:** *Fitts's law* — acquisition time ∝ distance/size; make frequent targets big
  and near, give small click targets generous hit-areas. *Hick's law* — decision time ∝ log(choices);
  limit options, use progressive disclosure. *Miller's law* — working memory ≈ 4±1 chunks; chunk and
  group. *Doherty threshold* — keep feedback < ~400ms or attention drifts.
- **Gestalt grouping** — proximity, similarity, common region, continuity, closure: spatial layout
  *is* communication; group related controls, separate unrelated ones.
- **Shneiderman's Visual-Information-Seeking Mantra:** *overview first, zoom and filter, then details
  on demand.* The backbone of any inspection/exploration UI.

## Domain pattern libraries (category conventions — steal, don't reinvent)

When the artifact is one of these, these are table-stakes patterns with settled conventions:

- **Timeline / animation / video editors:** frame-accurate scrubbing; draggable playhead; click-ruler
  to jump; **keyboard transport** (Space play/pause, ←/→ frame-step, Home/End to ends, J/K/L shuttle);
  zoomable time axis; **onion skinning** (ghost of past/future frames — cyan past, magenta future);
  dope sheet / value-curve graph modes; click-frame-counter to type an exact time; loop region;
  small-multiples / filmstrip overview. (OpenCut, Final Cut, Thirdrez/Kinetiq, VideoFlow all converge.)
- **Debugging / inspection / data-exploration tools:** show the **trace** (state over time), not
  isolated snapshots — don't make the user mentally reconstruct evolution (EPFL *Tracers* 2026);
  **global view of values in context** beats one-at-a-time (Anteater, Faust et al.); **coordinated
  views** with linked highlighting (select in one view → highlight in all; Hoffswell/Satyanarayan/Heer);
  overview+detail / focus+context; sparklines for value-over-time (Tufte); bidirectional source↔effect
  linking.

## Provenance
Grounded in the tools-for-thought canon: Victor (*Inventing on Principle*, *Learnable Programming*,
*Ladder of Abstraction*, *Magic Ink*), Norman (*Design of Everyday Things* — gulfs, affordances),
Engelbart (*Augmenting Human Intellect* — co-evolution), Sutherland (*Sketchpad* — direct
manipulation + constraints), Tufte (small multiples), Matuschak & Nielsen (*tools for thought*,
mnemonic medium), Ink & Switch (malleable / local-first software). HCI canon: Nielsen 10 (NN/G 1994),
Shneiderman 8 golden rules + visual-seeking mantra (cs.umd.edu/~ben, 2016), Fitts/Hick/Miller laws,
Gestalt grouping; inspection-tool literature (EPFL *Tracers* 2026; Anteater; Hoffswell/Satyanarayan/
Heer). See the companion research memos (e.g. anim-workbench
`docs/research/2026-06-18-tools-for-thought-interface-thinkers.md`).
