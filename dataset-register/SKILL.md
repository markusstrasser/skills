---
name: dataset-register
description: "Register an acquired dataset in the per-topic dataset catalog. Use when: you've just staged data via /data-acquisition, adding a new source to an existing topic, or formalizing an existing ad-hoc entry. Produces a standardized dataset card (provenance, access state, variables, known quirks) so future sessions don't re-probe or re-download. Card format is shared across topics."
user-invocable: true
argument-hint: "<topic> <dataset-id>"
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit]
effort: low
---

# Dataset Register

Normalize per-topic dataset catalogs. Existing examples:
- `research/immigration-dataset-register.md`
- `research/iq-sex-differences-dataset-cards.md`
- `research/iq-sex-differences-dataset-roadmap.md`

Goal: one card per dataset, queryable by grep, surviving across sessions.

---

## Card format

Append to `research/<topic>-dataset-register.md`:

```markdown
### <DATASET_ID> — <short name>

**Source:** <agency / provider>
**Acquired:** YYYY-MM-DD  [or Access-gated / In-progress / Blocked]
**Local path:** `sources/<topic>/data/external/stage3/<source>/<dataset>/`
**Official:** <landing URL>
**Codebook:** `<local codebook filename>` | <codebook URL>
**Size:** <N> files, <total MB>
**License:** <public-use / restricted / registration required>

**Key variables:**
- `<VAR>` — <meaning>
- `<VAR>` — <meaning>

**Known quirks:**
- <gotcha 1>
- <gotcha 2>

**Used in:**
- `research/<topic>-<memo>.md` (if already analyzed)
- `sources/<topic>/scripts/<script>.py` (if already coded)
```

---

## Minimal card (when you only have URL + path)

```markdown
### <DATASET_ID> — <short name>
**Source:** <agency>  **Acquired:** YYYY-MM-DD
**Local:** `sources/<topic>/data/external/stage3/<source>/<dataset>/`
**Official:** <url>
```

Expand when you actually use it.

---

## Register vs cards vs roadmap

| File | Purpose | When to use |
|---|---|---|
| `<topic>-dataset-register.md` | Flat list of what we have | Default. Update on every acquisition. |
| `<topic>-dataset-cards.md` | Long-form per-dataset notes | When a single dataset warrants >1 page of documentation. |
| `<topic>-dataset-roadmap.md` | What we want next + status | When planning acquisitions. Update `✅ acquired` / `🚧 gated` / `❌ blocked`. |

Three files can coexist for large topics (e.g., iq-sex-differences has all three).

---

## Deduplication rule

Before writing a new card, grep for the dataset ID:
```bash
grep -i "<DATASET_ID>" research/*-register.md research/*-cards.md research/*-roadmap.md
```

If found, **edit the existing card** — don't create a duplicate. Update `Acquired:`
date and add any new variables used.

---

## After registering

Commit with message like:
```
[research] Register <DATASET_ID> — <brief why>
```

Body (per commit-conventions.md for `research/` paths):
> Names the concept (dataset) and what changed directionally (added / updated / moved to acquired).

## Evidence

- Parallel formats across `research/immigration-dataset-register.md`,
  `research/iq-sex-differences-dataset-cards.md`, `research/iq-sex-differences-dataset-roadmap.md`
  → inconsistent card shape. This skill picks one.
