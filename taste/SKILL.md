---
name: taste
description: "Use when: building or restyling an app, interface, page, 3D scene, animation, diagram, poster or artwork and choosing a visual direction — pull exemplars from Markus's own saved media (Pinterest, Twitter, Instagram) before designing. NOT data-form choice (/figure) or interaction architecture (/interface-thinking)."
user-invocable: true
argument-hint: "[design brief]"
allowed-tools: [Bash, Read]
effort: low
---

# Taste

Markus's saved images and videos carry a vision-model description each. Search
them for the brief, look at the actual media, then design from what you saw.

```bash
just -f ~/Projects/personal/justfile taste "<brief>" -k 12
just -f ~/Projects/personal/justfile taste "<brief>" --kind interface,diagram-dataviz --json
```

Kinds: `art`, `interface`, `graphic-design`, `diagram-dataviz`, `3d-render`,
`architecture-interior`, `object-product`, `photography`. Results print the kind,
the path, and the description. For a video the path is a 2x2 frame grid in the
order 10/35/60/85% of the clip; `--json` also gives the original video `path`.

## How to use it

1. Run two or three searches that phrase the brief differently: the artifact
   ("analytics dashboard"), the quality ("dense tabular data, monospace"), and
   the feeling or medium ("print-like, muted palette").
2. Read the images of the best 6-10 hits with the Read tool. The description
   locates; the image decides. Drop hits that only matched on words.
3. Name what you take from each one you use: "grid and type scale from X,
   palette from Y". Borrow moves, never copy a whole piece.
4. Say which brief the references serve. Taste here depends on the job, so a
   reference that is right for a poster may be wrong for a settings screen.

## Limits

- Descriptions are written by a model (gpt-6-luna) and are unverified. They
  never record why Markus saved something.
- Saved items are all positives: the library knows what he kept, not what he
  rejects. Do not infer dislikes from absence.
- The library needs the 2TBPNY volume mounted to open media. If search
  reports a missing index, run `media taste index` (see the personal justfile).
- New saves get described with `just taste-update --apply` in the personal repo.
