---
name: person-into-scene
description: "Use when: photoreal Markus in scene template, 'put me in this photo', dating/lifestyle/cinematic shots, likeness fix. NOT generic image gen (/gpt-image-2)."
---

# Person-into-scene image generation

Put a SPECIFIC real person into a scene template, photorealistically, keeping their
actual identity. Built + battle-tested 2026-06-10 (Markus). Assets:
`~/Documents/image-gen/` (`scene-templates/`, `markus-references/`, `generated/`,
`MANIFEST.md`, `HANDOFF.md`). Code lives in `~/Projects/imagegen/` (own repo since
2026-06-10, split out of phenome) — run `just`/`uv` commands from there.

## ASK THE DESTINATION FIRST (before generating anything)

The output format decides scene orientation AND final crop — get it wrong and you
regenerate. Markus's images are for **dating apps (Hinge/Tinder/Bumble)**, not
iPhone wallpaper. (Assuming "iPhone Pro dimensions" = 19.5:9 screen ratio cost a
round-trip — he called it "way too thin." That's wallpaper, not a photo.) Confirm:
- **Dating-app photo (default):** generate **portrait** `--size 1024x1536`; finish
  with `cohere_photo.py --app safe` (3:4 master that survives all three) or per-app
  (`bumble` 3:4, `tinder`/`hinge` 4:5). Keep the subject centred WITH MARGIN — apps
  re-crop algorithmically.
- **Wallpaper (rare):** `--app`-less, use `cohere_photo.py --iphone` (19.5:9).
- **Landscape scenes** (e.g. camel-desert) LOSE most of the frame when cropped to
  portrait — generate them portrait from the start, don't crop a landscape down.
See `[[feedback_image_iphone_pro_dimensions]]`.

## The engine (plan d4712f73 — BUILT 2026-06-10): use it, don't hand-drive the stages

The slow human-in-the-loop is gone. One engine (`imagegen`, `src/imagegen/engine.py`) runs a whole
recipe from a declarative **identity-profile** + **shot-spec** YAML: gpt-image-2 generate
→ face-swap + BiRefNet matte (ONE warm Modal app, all models resident) → local finish/crop
→ **VLM auto-QC rank**. It surfaces the top 1–2 + flags so you read ~2 finalists, not ~40.

Three faces over the same engine — prefer them over hand-running the stages:
- **CLI:** `just image-run markus camel-desert` (or `scripts/tools/image_engine.py run --profile … --shot …`)
- **MCP (agent-native, preferred for agents):** `image_pipeline(profile="markus", shot="camel-desert")`
  on the `imagegen` MCP server (registered in `~/Projects/imagegen/.mcp.json`) — also
  `image_swap`, `image_finish`, `image_generate`, `image_engine_status`.
- **UI (human cull):** `just image-ui` — Gradio: generate → auto-ranked gallery → you pick;
  plus a FREE local re-finish tab (tweak soften/grain/crop with live preview, no regen).

Recipes live in `~/Documents/image-gen/profiles/markus.yaml` + `shots/*.yaml`. Deploy the
Modal app once per code change: `just image-deploy`. The four model weights coexist in one
container (numpy<2 ABI proven — `just image-probe`); re-validate if deps change.

**2026 SOTA re-check (research-validated, keep this architecture):** the generate-then-swap
decoupling is still correct — even Nano Banana Pro / FLUX / InfiniteYou reconstruct a face
*like* the person (~5%+ drift, no persistent identity), so the face-swap stays the identity-
truth step. Restorer A/B MEASURED 2026-06-10 (see backlog doc): **GPEN-BFR-1024 is the
default restore** — the only model that GAINS identity vs the raw swap (+0.002 bright,
+0.017 dark face) with natural texture; GFPGAN is runner-up (−0.01/−0.018, slight wax);
CodeFormer was REJECTED as default (−0.04, codebook prior pulls toward a generic face —
the memo's prediction didn't survive measurement). Override per profile/shot YAML:
`finish.restorer: gfpgan|codeformer|gpen_bfr_1024`. Remaining candidates in
`~/Projects/imagegen/docs/research/image-engine-upgrade-backlog.md`:
Nano Banana Pro as generator, DreamID / BFS diffusion head-swap (probed via
`scripts/modal/bfs_head_swap_probe.py`).

## THE core architecture — read first (it's why this works)

**Identity is IMPOSED, never GENERATED.** gpt-image-2 (and every diffusion model)
*cannot* reproduce a specific real face from references — it averages refs into a
generic-handsome-model face. Do NOT try to fix likeness with more refs or better
prompts; that's a model ceiling and chasing it wastes rounds + money (it already
cost a full session once). Instead, two stages:

1. **Scene + body + pose + lighting** → `gpt-image-2` (it's great at this).
2. **Identity** → **face-swap the real face in** with InsightFace `inswapper`
   (real pixels, faithful, no AI-face look).

Same principle as the photo-cleanup tool (`clean_ai_photo.py`): never trust
diffusion with the face; paste/swap the real one as a post-step.

## Tools (the engine + its three faces; the per-stage code below is "under the hood")

- **Engine library:** `imagegen` (`~/Projects/imagegen/src/imagegen/`) — `run_pipeline(profile, shot)` does the whole
  recipe and returns ranked variants (`run.json` sidecar). `load_profile`/`load_shot`,
  `finish_image`/`FinishSpec`, `build_prompt`, `judge_image` are also exported.
- **Unified Modal app (`image-engine`):** `scripts/modal/image_engine_modal.py` — ONE app
  with buffalo_l + inswapper + GFPGAN + BiRefNet resident. `swap_and_matte` (engine path);
  one-off CLI: `::swap` (batch swap+matte), `::matte` (matte only), `::smoke` (single).
  `just image-deploy` after edits. Replaces the old face-swap + birefnet apps (3→1).
- **Stage CLIs (now thin wrappers over the engine — single source of logic):**
  `scripts/tools/imagegen_scene.py` (gen only, → `gen.py`),
  `scripts/tools/cohere_photo.py` (finish only, → `finish.py`). Use the engine CLI/MCP for
  the full flow; reach for these only for a single isolated stage.
- **De-swirl (DEMOTED — last resort):** `scripts/modal/clean_ai_photo.py`. For gpt-image-2
  skin artifacts, reproduce-clean (regen + swap) beats de-swirl; use it ONLY to preserve an
  exact existing frame you can't regenerate. NOT in the engine hot path.
- **enhance** (swap-side face restore, GPEN-BFR-1024 by default) lives in the profile
  (`enhance: 0.6`); blend 0.3 (subtle) → 0.7 (crisp), Markus rejects plastic so don't
  exceed ~0.7. `finish.restorer:` switches the model (gfpgan | codeformer | gpen_bfr_1024).
- **Best matte model (2026):** BiRefNet (MIT, hair-grade). SAM 3 (Meta, ICLR 2026) gives
  instance/concept masks not alpha mattes — only for text-targeting a specific bg entity.

## Workflow

```
# PRIMARY — one recipe, end to end (gen → swap+matte → finish → auto-QC rank):
just image-deploy            # once per engine code change (cached image ⇒ ~2s)
just image-run markus camel-desert        # bare names under ~/Documents/image-gen/
#   → ranked gallery in generated/engine-runs/<ts>-…/final/, top pick + flags printed.
#   MCP: image_pipeline(profile="markus", shot="camel-desert")
#   UI:  just image-ui   (human cull + free local re-finish with live preview)

# A shot is a small YAML diff against the profile (shots/<name>.yaml):
#   scene: camel-desert.jpg
#   scene_desc: "..."; gaze: away; n: 3
#   extra: "subtle Burning Man cues, faint distant mutant vehicles"   # de-genericise trick
#   target: {app: safe}                  # bumble|tinder|hinge|safe|wallpaper

# UNDER THE HOOD (only for a single isolated stage):
#   gen:    uv run --with openai python3 scripts/tools/imagegen_scene.py --scene … --n 4
#   swap+matte: uvx --with modal modal run scripts/modal/image_engine_modal.py::swap \
#                 --targets "a.png,b.png" --source selfie_2026-02-10.jpg --out-dir out/
#   finish: uv run python3 scripts/tools/cohere_photo.py --input swap.png --matte m.png \
#             --output final.png --downscale 0.92 --soften 0.7 --grain 3 --app safe
```

## Locked recipe (don't re-derive — all dialed across the 2026-06-10 session)

- **Face refs: casual selfies, NOT studio portraits** (studio → smug/"douchy"):
  `img_1901`, `selfie_2026-04-22`, `selfie_2026-02-10`, `selfie_2026-03-04`.
- **Swap source (the face imposed in stage 2):** `selfie_2026-02-10` — proven best
  this session (likeness 0.92–0.95, recent clear frontal). Default to it.
- **Body refs:** `photo_2017-01-22` (frame) + `24698343-...png` (BULK shape — Markus
  wants the fuller, broad-shouldered build, not lean).
- **Bulk body-desc** (pass via `--body-desc`): "fit muscular male-model physique,
  broad shoulders, full developed chest, strong defined arms — more muscular than
  lean, athletic but natural, never gross/vascular bodybuilder; even tan, smooth
  skin, no chest hair, no bulging veins."
- **Gaze: usually `away`** — Markus prefers NOT looking into the camera (candid).
- **Veins:** a few natural forearm veins are FINE — *not extreme*, *NONE on hands*
  (biceps a touch ok but unneeded). Do NOT prompt "no veins whatsoever" (over-smooth).
- **Background context trick:** to de-genericise a scene, add "subtle signs of
  [place], faint distant [objects], hazy, not crowded" to `--scene-desc`/`--extra`.
  Worked well for Burning Man (mutant vehicles/art on the playa horizon).
- **Face blur:** inswapper's 128px face reads softer than the body — pass `--enhance
  0.6` on the swap (GPEN-1024 restore, the measured default). Tune 0.3–0.7; he rejects
  plastic, don't exceed ~0.7.
- **Finish = SUBTLE, not bokeh** (`[[feedback_image_finish_subtle_not_bokeh.md]]`):
  light grain + background MOSTLY IN FOCUS. `cohere_photo.py --downscale 0.92
  --soften 0.7 --grain 3`. Heavy matte-DoF bokeh reads "too professional/staged" —
  keep `--soften ≤1.5`. The BiRefNet matte still helps keep the subject crisp + a
  GENTLE background touch; just don't crank it.
- **Polaroid look** (when asked): `cohere_photo.py --polaroid [--polaroid-lift 8 for
  night] [--border]` — instant-film grade (lifted blacks, warm cast, vignette, grain).
- **Reproduce-clean > de-swirl** for gpt-image-2 skin artifacts (waxy/swirly chest):
  REGENERATE the scene via `imagegen_scene.py` (anti-artifact prompt) then swap, NOT
  `clean_ai_photo.py` de-swirl. De-swirl is only for preserving an exact existing frame.
- **Run n=3–4, cull by face-similarity (+ eye), keep best 1–2.**

## gpt-image-2 facts (verified 2026-06-09)

- Quality: `low|medium|high|auto` — **no `xhigh`**. high ≈ $0.21/img + ref input tokens
  (~$0.26 with refs).
- `input_fidelity` is **auto-high** for gpt-image-2 — omit it (passing it can error).
- Person-in-scene compositing is officially supported; anchor realism with natural
  lighting, no cinematic grading.

## READ BEFORE YOU CLAIM (hook-enforced in ~/Projects/imagegen)

Never present an image as "fixed/clean/final" without verifying it. The verification
stack, in order of authority:
1. **Flash localizer (primary):** `uv run python3 scripts/tools/flash_inspect.py img.png`
   (in ~/Projects/imagegen) — schema-constrained gemini-3-flash artifact findings with
   severity score + box_2d. Run it on every candidate BEFORE presenting; when a defect
   appears, BISECT stages with it (gen → swap → finish variants — it isolated the A3
   color-match root cause in one pass after agent eyes missed it six times).
2. **Your own Read (secondary):** the exact file being sent, full frame AND native-res
   crops of any region you make claims about. Thumbnails/contact sheets hide discs,
   washes, seams. Draw mask/patch rectangles on the image before trusting measurements
   through them.
A PreToolUse hook in imagegen blocks SendUserFile for never-Read images; honor the
spirit, not just the gate. After fixing a pipeline bug, regenerate canonical-named
outputs in place (stale plain-named files are what the user opens).

## Hard line

Never use the face-swap to deceive real people (dating-profile catfishing, fraud,
impersonating someone else). It's for the subject's own generated art only.
