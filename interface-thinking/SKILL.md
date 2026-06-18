---
name: interface-thinking
description: "Use when: designing/critiquing any interface, editor, tool, UI, or feedback loop; 'how should this feel', 'why is this clunky', closing the gap between intent and effect. Lenses from Victor/Norman/Engelbart/Matuschak. NOT visual styling (/frontend-design) or ideation (/brainstorm)."
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

## Provenance
Grounded in the tools-for-thought canon: Victor (*Inventing on Principle*, *Learnable Programming*,
*Ladder of Abstraction*, *Magic Ink*), Norman (*Design of Everyday Things* — gulfs, affordances),
Engelbart (*Augmenting Human Intellect* — co-evolution), Sutherland (*Sketchpad* — direct
manipulation + constraints), Tufte (small multiples), Matuschak & Nielsen (*tools for thought*,
mnemonic medium), Ink & Switch (malleable / local-first software). See the companion research memo
pattern (e.g. anim-workbench `docs/research/2026-06-18-tools-for-thought-interface-thinkers.md`).
