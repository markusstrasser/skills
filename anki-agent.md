# Visual Content for Anki Cards

Guidelines for creating images, diagrams, and animations for spaced repetition flashcards.

## Format Tradeoffs

| Format | Pros | Cons | Best For |
|--------|------|------|----------|
| **SVG** | Crisp at any size, small file, editable | No animation, some rendering quirks in Anki | Mathematical diagrams, simple illustrations |
| **PNG** | Universal support, predictable rendering | Large files at high DPI, blurry if scaled up | Screenshots, photos, complex renders |
| **GIF** | Animation support, wide compatibility | Limited colors (256), large files, no transparency animation | Simple step-by-step animations |
| **WebP** | Small files, animation support, good quality | Limited Anki support (test first) | Modern alternative to PNG/GIF |

## Recommended Approaches

### Mathematical Diagrams → SVG via TikZ or Penrose

**TikZ (node-tikzjax):**
```javascript
import tikzjax from 'node-tikzjax';

const tex = `
\\begin{document}
\\begin{tikzpicture}
  \\node (A) at (0,0) {$G$};
  \\node (B) at (2,0) {$H$};
  \\draw[->] (A) -- (B) node[midway, above] {$\\phi$};
\\end{tikzpicture}
\\end{document}
`;

const svg = await tikzjax.default(tex);
// Save to Anki media folder
```

**Penrose** (for automatic layout):
```bash
roger trio diagram.trio.json > output.svg
```

### Animated Explanations → GIF via Manim

For step-by-step reveals or transformations:

```python
from manim import *

class CardAnimation(Scene):
    def construct(self):
        eq1 = MathTex(r"x^2 - 4 = 0")
        eq2 = MathTex(r"x = \pm 2")

        self.play(Write(eq1))
        self.wait(0.5)
        self.play(TransformMatchingTex(eq1, eq2))
        self.wait(0.5)
```

```bash
# Render as GIF (small, looping)
manim -ql --format gif card_animation.py CardAnimation
```

**GIF considerations:**
- Keep under 5 seconds (attention span)
- Use low quality (`-ql`) for smaller files
- Loop seamlessly if possible
- 15fps is usually sufficient

### Static Math → LaTeX in Anki

For simple equations, use Anki's built-in LaTeX:
```
[$]\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}[/$]
```

Only create images when:
- Diagram is complex (graphs, commutative diagrams)
- Need specific styling not available in Anki
- Want consistent rendering across devices

## Sizing Guidelines

**Anki card dimensions:**
- Desktop: ~600-800px wide typical
- Mobile: ~300-400px wide
- **Target:** 600px wide, auto height

**For SVGs:**
```svg
<svg width="600" viewBox="0 0 600 400">
```

**For PNGs:**
- Render at 2x (1200px) for retina displays
- Or use 150-200 DPI

**For GIFs:**
- 480px wide max (file size)
- 15fps (balance quality/size)

## Anki Media Integration

### Adding to Anki via MCP

```python
# Store media file
mcp__anki__mediaActions(
    action="storeMediaFile",
    filename="group_homomorphism.svg",
    data=base64_encoded_svg
)

# Create note with image
mcp__anki__addNote(
    deckName="Abstract Algebra",
    modelName="Basic",
    fields={
        "Front": "What is this diagram showing?",
        "Back": '<img src="group_homomorphism.svg">'
    }
)
```

### File naming conventions
- Lowercase with hyphens: `kernel-image-theorem.svg`
- Include topic prefix: `galg-quotient-group.svg`
- Avoid spaces and special characters

## Tool Selection by Content Type

| Content | Tool | Output |
|---------|------|--------|
| Commutative diagrams | TikZ (tikz-cd) | SVG |
| Set theory / Venn | Penrose | SVG |
| Function graphs | Manim or Typst/CeTZ | SVG/PNG |
| Step-by-step proofs | Manim | GIF |
| 3D surfaces | Asymptote or Manim | PNG |
| Architecture/flowcharts | D2 | SVG |
| Category theory | Penrose or TikZ | SVG |

## Quality vs File Size

**For daily review cards:**
- Prioritize fast loading
- PNG: 72-100 DPI sufficient
- GIF: 10-15fps, 480px max
- SVG: Simplify paths if complex

**For reference/study cards:**
- Higher quality acceptable
- PNG: 150-200 DPI
- Can use larger GIFs

## Common Patterns

### Theorem visualization card
```
Front: [SVG diagram of theorem setup]
Back: [Same diagram with proof annotations]
```

### Definition with example
```
Front: Define [concept]
Back: [Definition text] + [SVG example diagram]
```

### Process/algorithm card
```
Front: How does [algorithm] work?
Back: [GIF showing steps] or [Series of SVG frames]
```

### Comparison card
```
Front: Compare [A] vs [B]
Back: [Side-by-side SVG diagrams]
```

## Gotchas

1. **SVG in Anki:** Some CSS/JS features don't work. Test in Anki before mass-producing.

2. **GIF file sizes:** A 5-second GIF can easily hit 2-5MB. Keep animations short.

3. **LaTeX in images:** When using TikZ, ensure math renders correctly. Test `$...$` vs `\(...\)`.

4. **Mobile rendering:** Always test on phone. Complex SVGs may render slowly.

5. **Anki media sync:** Large media files slow down AnkiWeb sync. Optimize aggressively.

6. **Dark mode:** Design diagrams that work on both light and dark backgrounds, or create variants.
