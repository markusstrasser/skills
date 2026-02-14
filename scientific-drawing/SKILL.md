---
name: scientific-drawing
description: Generate scientific diagrams, figures, and illustrations using Typst/CeTZ, Asymptote, Penrose, TikZ, or D2. Use when creating mathematical diagrams, technical illustrations, scientific figures, vector graphics, 3D plots, architecture diagrams, flowcharts, ERDs, network diagrams, or converting mathematical notation to visual representations. Automatically selects the best tool based on the task.
allowed-tools: Bash, Read, Write, Grep, Glob
---

# Scientific Drawing & Diagram Generation

Comprehensive skill for generating high-quality scientific diagrams using the right tool for the job: Typst/CeTZ, Asymptote, Penrose, TikZ, or D2.

## For Anki Card Diagrams (Primary Workflow)

### Path Selection

| Your request needs... | Use this path |
|----------------------|---------------|
| LaTeX math in the diagram, 3D perspective, complex biological structures, circuits, commutative diagrams | **TikZ** |
| Schematic comparisons, bar charts, process flows, gradients, number lines, inline on card | **Inline SVG** |
| Uncertain | **TikZ** (proven 7/7 first-try reliable) |

### TikZ Path

1. **Find the closest template** in `diagrams/templates/`:
   - `bar_comparison.tex`, `process_flow.tex`, `number_line.tex`, `cycle_diagram.tex`, `bipolar_axis.tex`
2. **Adapt the template** — use only `anki*` color names from `diagrams/preamble_anki.tex`
3. **Compile**: `uv run python scripts/anki_tikz.py compile <file.tex> --verify`
4. **Inspect** the opened PNG — check scientific accuracy, not just rendering
5. **Iterate** if needed (max 3 rounds), then attach to card via AnkiConnect

### Inline SVG Path

1. **If standard pattern** — use the generator:
   ```bash
   uv run python scripts/generate_card_svg.py bar --values "36,32,2" --labels "A,B,C"
   uv run python scripts/generate_card_svg.py flow --steps "A,B,C"
   uv run python scripts/generate_card_svg.py numberline --range "0,14" --markers "7:neutral"
   uv run python scripts/generate_card_svg.py gradient --range "380,700" --markers "450:blue"
   uv run python scripts/generate_card_svg.py fold --baseline "4" --fold "34" --labels "A,B"
   ```
2. **If custom** — write SVG by hand following `docs/ANKI_DESIGN_LANGUAGE.md`
3. **Validate**: `uv run python scripts/validate_card_svg.py <file_or_stdin>`
4. **Paste** SVG string directly into card HTML Back field

### Quality Gates

- Passes `validate_card_svg.py` with 0 errors (SVG path)
- Compiles first try (TikZ path)
- Scientific accuracy verified (not just "it renders")
- Passes Reconstruction Test: "Does seeing this make me go 'oh right'?"
- Tag card `ai-visual` and `ai-modified`

---

## For Standalone Diagrams (Other Workflows)

## Tool Selection Guide

### When to use each tool

**Typst + CeTZ** - Modern, Fast, Great for Papers
- 2D diagrams with TikZ-like API
- Plotting and charts
- Tree layouts
- Integration with Typst documents
- Millisecond compilation
- ✅ Use for: Quick iterations, modern workflows, integrated documents

**Asymptote** - Powerful 3D Graphics
- 3D scientific visualizations
- Technical drawings with precise coordinates
- LaTeX-quality output
- PostScript/PDF/SVG export
- ✅ Use for: 3D graphics, precise technical drawings, publication figures

**Penrose** - Automatic Layout from Math Notation
- Mathematical diagrams from notation
- Set theory, category theory diagrams
- Graph visualization
- Automatic constraint-based layout
- ✅ Use for: Abstract math diagrams, when you want separation of content/style

**TikZ (via node-tikzjax)** - Most Flexible, Largest Ecosystem
- Circuit diagrams, flowcharts, mind maps
- Huge library ecosystem
- Web rendering via JavaScript
- LaTeX integration
- ✅ Use for: Complex diagrams with existing TikZ code, specialized diagrams

**D2** - Modern Declarative Diagramming
- Modern text-to-diagram DSL
- Architecture diagrams, network diagrams, flowcharts
- Built-in themes and layouts
- Fast compilation
- SQL tables and class diagrams
- ✅ Use for: Software architecture, system diagrams, ERDs, modern workflows

## Prerequisites

### Installation

```bash
# Typst (for CeTZ)
brew install typst  # macOS
# or: curl -fsSL https://typst.app/install.sh | sh

# Asymptote
brew install asymptote  # macOS
# or: apt-get install asymptote  # Linux

# D2
curl -fsSL https://d2lang.com/install.sh | sh | sh
# or: brew install d2  # macOS

# Node dependencies (Penrose, TikZ)
cd ~/Projects/skills/scientific-drawing
bun install

# Python dependencies (if needed for automation)
uv pip install pypdf pdfplumber
```

Check installations:
```bash
./scripts/check-tools.sh
```

## Quick Start

### Helper Scripts

All tools are accessible through unified helper scripts:

```bash
# Generate diagram (auto-detects type)
./scripts/generate.sh input.typ          # Typst/CeTZ
./scripts/generate.sh input.asy          # Asymptote
./scripts/generate.sh input.trio.json    # Penrose
./scripts/generate.sh input.tikz.tex     # TikZ
./scripts/generate.sh input.d2           # D2

# Specify output format
./scripts/generate.sh input.typ pdf
./scripts/generate.sh input.asy svg --no-view
./scripts/generate.sh input.d2 svg -t 101  # D2 with theme

# Batch process
./scripts/batch-generate.sh ./diagrams/

# Interactive preview
./scripts/preview.sh input.typ  # Opens watch mode
d2 --watch input.d2              # D2 watch mode
```

## Detailed Tool Usage

### Typst + CeTZ

CeTZ provides a drawing library for Typst with an API inspired by TikZ.

**Basic diagram:**
```typst
#import "@preview/cetz:0.2.2": canvas, draw, plot

#canvas({
  import draw: *

  // Simple shapes
  circle((0, 0), radius: 1, fill: blue.lighten(80%))
  line((0, 0), (2, 1), stroke: red)

  // With labels
  content((1, 0.5), [Hello])
})
```

**Plotting:**
```typst
#import "@preview/cetz:0.2.2": canvas, plot

#canvas({
  plot.plot(size: (8, 6),
    x-label: [Time],
    y-label: [Value],
    {
      plot.add(
        domain: (0, 2*calc.pi),
        x => calc.sin(x)
      )
    }
  )
})
```

**Compile:**
```bash
typst compile diagram.typ diagram.pdf
# or use helper
./scripts/generate.sh diagram.typ
```

See [examples/typst-cetz/](examples/typst-cetz/) for more examples.

### Asymptote

Powerful vector graphics language with 3D support.

**Basic 2D:**
```asymptote
import graph;
size(200);

draw(unitcircle, blue);
dot((0,0), red);

label("Origin", (0,0), S);
```

**3D Graphics:**
```asymptote
import graph3;
size(200);

currentprojection=orthographic(4,2,3);

// Draw 3D surface
draw(surface(f=(x,y){return x^2+y^2;},
    (-1,-1), (1,1), nx=20, ny=20),
    lightblue+opacity(0.7));

// Add axes
axes3("$x$", "$y$", "$z$");
```

**Compile (non-interactive):**
```bash
asy -f pdf -noV diagram.asy
# or use helper
./scripts/generate.sh diagram.asy pdf --no-view
```

**Configuration for automation:**
Create `~/.asy/config.asy`:
```asymptote
import settings;
settings.outformat="pdf";
settings.interactiveView=false;
settings.batchView=false;
settings.render=4;
```

See [examples/asymptote/](examples/asymptote/) for more examples.

### Penrose

Automatically generate diagrams from mathematical notation.

**Trio structure:**
Three files define a diagram:

1. **Domain** (`.domain`) - Type definitions
2. **Substance** (`.substance`) - Declarations
3. **Style** (`.style`) - Visual rules

**Example - Set theory:**

`setTheory.domain`:
```
type Set
predicate Subset(Set, Set)
predicate Intersect(Set, Set)
```

`diagram.substance`:
```
Set A, B, C
Subset(A, B)
Intersect(B, C)
```

`venn.style`:
```
forall Set x {
    x.shape = Circle {
        strokeWidth: 2
    }
}

forall Set A; Set B
where Subset(A, B) {
    ensure contains(B.shape, A.shape)
}
```

**Trio JSON:**
```json
{
  "domain": "./setTheory.domain",
  "style": ["./venn.style"],
  "substance": "./diagram.substance",
  "variation": "seed-123"
}
```

**Generate:**
```bash
bunx @penrose/roger trio diagram.trio.json > output.svg
# or use helper
./scripts/generate.sh diagram.trio.json
```

**Programmatic usage:**
```javascript
import { compile, optimize, toSVG } from "@penrose/core";

const trio = {
  domain: "type Set\npredicate Subset(Set,Set)",
  substance: "Set A, B\nSubset(A, B)",
  style: "forall Set x { x.shape = Circle { } }"
};

const compiled = await compile(trio);
const optimized = optimize(compiled.value);
const svg = await toSVG(optimized.value, async () => undefined);
```

See [examples/penrose/](examples/penrose/) for more examples.

### TikZ (via node-tikzjax)

Use TikZ with JavaScript/Node rendering.

**Basic usage:**
```javascript
import tikzjax from 'node-tikzjax';

const tikzCode = `
\\begin{document}
\\begin{tikzpicture}
  \\draw[thick, ->] (0,0) -- (2,0) node[right] {$x$};
  \\draw[thick, ->] (0,0) -- (0,2) node[above] {$y$};
  \\draw[color=red] (0,0) circle (1cm);
\\end{tikzpicture}
\\end{document}
`;

const svg = await tikzjax.default(tikzCode);
console.log(svg);  // SVG output
```

**With helper script:**
```bash
./scripts/tikz-render.js diagram.tikz.tex > output.svg
# or use unified helper
./scripts/generate.sh diagram.tikz.tex
```

**Complex diagrams:**
```tex
\\begin{document}
\\begin{tikzpicture}[domain=0:4]
  \\draw[very thin,color=gray] (-0.1,-1.1) grid (3.9,3.9);
  \\draw[->] (-0.2,0) -- (4.2,0) node[right] {$x$};
  \\draw[->] (0,-1.2) -- (0,4.2) node[above] {$f(x)$};
  \\draw[color=red] plot (\\x,\\x) node[right] {$f(x) =x$};
  \\draw[color=blue] plot (\\x,{sin(\\x r)}) node[right] {$f(x) = \\sin x$};
\\end{tikzpicture}
\\end{document}
```

See [examples/tikz/](examples/tikz/) for more examples.

### D2 (v0.7+)

Modern declarative diagramming language with automatic layout.

**Basic diagram:**
```d2
# Simple architecture
frontend -> backend: API calls
backend -> database: queries
database: PostgreSQL {shape: cylinder}
```

**Version 0.7+ Features:**

**1. Icons on connections:**
```d2
server -> client: {
  icon: https://icons.terrastruct.com/essentials/072-network.svg
}
```

**2. Rich content labels (markdown, LaTeX, code):**
```d2
algorithm: |md
  ## Binary Search
  ```python
  def binary_search(arr, x):
      left, right = 0, len(arr)-1
  ```
  Time: $O(\log n)$
|
```

**3. Legends:**
```d2
legend: {
  critical: {style.fill: red}
  warning: {style.fill: yellow}
  ok: {style.fill: green}
}
```

**4. SQL Tables (best with TALA/ELK layout):**
```d2
users: {
  shape: sql_table
  id: int {constraint: primary_key}
  email: varchar(255) {constraint: unique}
  created_at: timestamp
}

posts: {
  shape: sql_table
  id: int {constraint: primary_key}
  user_id: int {constraint: foreign_key}
  title: varchar(255)
}

posts.user_id -> users.id
```

**5. suspend/unsuspend for reusable models:**
```d2
suspend: true
template_node: {
  style.fill: blue
  style.stroke: black
}
unsuspend

# Use template
node1: @template_node
node2: @template_node
```

**Layout engines:**
```bash
# Default (dagre)
d2 input.d2 output.svg

# TALA (best for architecture, supports more features)
d2 --layout=tala input.d2 output.svg

# ELK (good for hierarchical)
d2 --layout=elk input.d2 output.svg
```

**Themes:**
```bash
# List available themes
d2 themes

# Apply theme
d2 -t 101 input.d2 output.svg  # Grape Soda
d2 -t 200 input.d2 output.svg  # Terminal (uppercase, monospace)
```

**Validation:**
```bash
# Check syntax before rendering
d2 validate input.d2
```

**Watch mode:**
```bash
d2 --watch input.d2 output.svg
```

**Glob filtering (v0.7):**
```d2
# Filter edges by node properties
*.style.fill: blue

&src.style.fill: blue  # Filter by source node
&level: 2              # Filter by nesting level
```

**Best for scientific diagrams:**
- System architecture diagrams
- Database schema (ERDs)
- Network topology
- Flowcharts and process diagrams
- Software architecture with C4 models

**Information Design Best Practices:**

**1. Compact layouts for essay illustrations:**
```d2
# Use explicit dimensions to control padding
GoalRoot: {
  label: "GOAL ROOT (chips, goal-diffs)"
  width: 420    # Explicit width reduces horizontal padding
  height: 60
}

# Horizontal layouts for groupings save vertical space
Memories: {
  label: "SHARED MEMORIES"
  direction: right  # Not down!

  PrefGraph: {label: "PREFERENCE\nGRAPH"; width: 120; height: 70}
  ActionPrior: {label: "ACTION\nPRIORS"; width: 120; height: 70}
  Knowledge: {label: "KNOWLEDGE\nGRAPH"; width: 120; height: 70}
}
```

**2. Abbreviated labels maintain clarity:**
```d2
# Too verbose (adds horizontal padding)
Orchestrator: {
  label: "PLANNER / ORCHESTRATOR\n(LLM router for task delegation)"
}

# Better (more compact)
Orchestrator: {
  label: "ORCHESTRATOR (LLM router)"
}
```

**3. Layout engine selection:**
```bash
# Dagre: Default, but doesn't respect container widths well
d2 --layout=dagre input.d2 output.svg

# ELK: Better vertical alignment, respects explicit dimensions
d2 --layout=elk input.d2 output.svg

# TALA: Best features but requires Pro license
d2 --layout=tala input.d2 output.svg
```

**4. Semantic color coding:**
```d2
# Color by flow type
GoalRoot -> Orchestrator: intent {
  style.stroke: "#2b6cb0"  # Blue: top-down intent
  style.stroke-width: 2
}

Evaluation -> Memories.PrefGraph: learn {
  style.stroke: "#2f855a"  # Green: forward/learning
  style.stroke-dash: 3     # Dashed: data flow
}

ConsistencyCenter -> GoalRoot: raise diffs {
  style.stroke: "#c05621"  # Orange: repair/ripple
  style.stroke-dash: 3
}

Evaluation -> GoalRoot: conflicts {
  style.stroke: "#b91c1c"  # Red: conflicts/escalation
  style.stroke-dash: 5
}

# Logging (de-emphasized)
GoalRoot -> EventLog: log {
  style.stroke: "#9ca3af"  # Gray
  style.opacity: 0.4       # Very subtle
}
```

**5. Global styles for consistency:**
```d2
direction: down

*.style.border-radius: 4
*.style.stroke: "#1f2937"
*.style.fill: "#ffffff"
*.style.stroke-width: 1
*.style.font-size: 13
```

**6. Typography hierarchy:**
```d2
Title: {
  label: "Main System Architecture"
  shape: text
  style.font-size: 18
  style.bold: true
  style.stroke: "#1f2937"
}

# Regular nodes default to font-size: 13 (set globally)
```

**7. Padding control:**
```bash
# Reduce padding (useful for tight layouts)
d2 --pad 10 input.d2 output.svg

# Specific dimensions for export
d2 --width 750 input.d2 output.png  # Force specific width
```

**8. Controlling layout with cyclic graphs (feedback loops):**

When your diagram has backward edges (feedback loops), automatic layout engines may place nodes in unexpected positions. Use `near` constraints to override:

```d2
# Problem: Feedback loops confuse layout algorithms
# ELK places nodes with many incoming edges at the bottom

TopNode: {
  label: "Should be at top"
  near: top-center    # Force to top despite backward edges
}

MiddleNode: {
  label: "Middle component"
}

BottomNode: {
  label: "Should be at bottom"
  near: bottom-center  # Anchor at bottom
}

# Forward flow
TopNode -> MiddleNode: forward
MiddleNode -> BottomNode: forward

# Feedback loops (don't affect layout hierarchy with near constraints)
BottomNode -> TopNode: feedback
MiddleNode -> TopNode: feedback
```

**Key insights for cyclic graphs:**
- `near: top-center` / `near: bottom-center` override automatic layout
- Useful for hierarchical diagrams with feedback loops
- Keeps logical "root" nodes at top even when they receive many incoming edges
- Works with ELK layout engine
- Alternatives: `near: top-left`, `near: top-right`, etc.

**Common use cases:**
- Control loops (feedback from sensors to controllers)
- Iterative algorithms (results feeding back to input)
- Closed-loop systems (output affecting input)
- Hierarchical structures with backward dependencies

**Typical compact diagram workflow:**
1. Start with clear system design concepts
2. Abbreviate labels (keep essential info only)
3. Use horizontal layouts where it makes sense (groupings, categories)
4. Set explicit widths/heights to control padding
5. Use ELK layout for better vertical flow
6. Apply semantic color coding (blue=intent, green=forward, orange=repair, red=conflict)
7. De-emphasize non-critical connections (logging) with opacity
8. Export at specific dimensions for target medium

**9. Debugging & Fixing D2 Diagrams:**

When layout engines produce overlapping labels or unexpected positioning, follow this debugging workflow:

**Step 1: Try different layout engines**
```bash
# Default dagre - good for simple hierarchies
d2 input.d2 output.png

# ELK - better for complex vertical flows
d2 --layout elk input.d2 output.png

# Compare both to see which handles your diagram better
```

**Step 2: Verify SVG output**

When you see overlapping text or positioning issues, generate SVG and inspect:

```bash
# Generate SVG for debugging
d2 --layout elk input.d2 output.svg

# Find overlapping labels
grep -n "label-name\|other-label" output.svg
```

SVG text elements show their position:
```svg
<text x="323.000000" y="-5.000000" ...>intent</text>
<text x="322.500000" y="-5.000000" ...>revise</text>
```

If two labels have the same (or very close) `y` coordinate, they overlap!

**Step 3: Last-resort SVG editing**

When layout engines can't resolve overlaps, manually adjust SVG:

```bash
# Example: Move "revise" label up by 27 pixels
sed 's/\(<text x="322.500000" y="\)-5.000000\(" .*>revise<\/text>\)/\1-32.000000\2/' \
  input.svg > output-fixed.svg

# Convert back to PNG
convert -density 150 -background white output-fixed.svg output-fixed.png
```

**Common fixes:**
- **Vertical overlap**: Adjust `y` coordinate (increase to move down, decrease to move up)
- **Horizontal overlap**: Adjust `x` coordinate
- **Multiple overlaps**: Use a script to batch-adjust

**Step 4: Create a verification script**

```bash
#!/bin/bash
# d2-check-overlaps.sh - Find overlapping text in D2 SVG output

svg="$1"
threshold=20  # Pixels - labels closer than this might overlap

# Extract all text positions and labels
grep '<text' "$svg" | \
  sed -n 's/.*x="\([^"]*\)" y="\([^"]*\)".*>\([^<]*\)<\/text>/\1 \2 \3/p' | \
  sort -n -k2 | \  # Sort by y coordinate
  awk -v thresh="$threshold" '
    NR > 1 {
      if ($2 - prev_y < thresh && $2 - prev_y > -thresh) {
        print "OVERLAP: " prev_label " (y=" prev_y ") and " $3 " (y=" $2 ")"
      }
    }
    { prev_y = $2; prev_label = $3 }
  '
```

**When to use manual SVG editing:**
- Layout engines place feedback loop labels at same position
- Complex cyclic graphs with many backward edges
- Labels that must stay close to specific nodes
- Fine-tuning for publication-quality diagrams

**Alternative: Adjust D2 source instead**

Sometimes you can work around overlaps by:
- Reordering connection declarations (changes routing)
- Adding invisible spacer nodes
- Splitting complex diagrams into multiple simpler ones
- Using different arrow routing (straight vs curved)

**Reference D2 repo:** `~/Projects/best/d2` contains source and examples.

See [examples/d2/](examples/d2/) for scientific diagram examples.

## Practical Tips & Gotchas

### TikZ (node-tikzjax) Critical Requirements

**MUST wrap in document tags:**
```tex
\begin{document}
\begin{tikzpicture}
  % your code here
\end{tikzpicture}
\end{document}
```

Without `\begin{document}...\end{document}`, node-tikzjax silently fails and produces empty output.

**Installation for CLI use:**
```bash
# Global install
bun add -g node-tikzjax

# Verify
bun pm ls -g | grep tikzjax
```

**Commutative diagrams (tikz-cd):**
```tex
\begin{document}
\begin{tikzcd}
  A \arrow[r, "f"] \arrow[d, "g"'] & B \arrow[d, "h"] \\
  C \arrow[r, "k"'] & D
\end{tikzcd}
\end{document}
```

**Programmatic usage (preferred):**
```javascript
import tikzjax from 'node-tikzjax';

const tex = `
\\begin{document}
\\begin{tikzpicture}
  \\node (A) at (0,0) {$A$};
  \\node (B) at (2,0) {$B$};
  \\draw[->] (A) -- (B) node[midway, above] {$f$};
\\end{tikzpicture}
\\end{document}
`;

const svg = await tikzjax.default(tex);
// svg is a string containing the SVG markup
```

### Penrose Workflow

**Understanding the three-file architecture:**

1. **Domain (.domain)** - Type system for your mathematical objects:
```
type Group
type Homomorphism
predicate Isomorphism(Homomorphism)
function dom(Homomorphism h) -> Group
function cod(Homomorphism h) -> Group
```

2. **Substance (.substance)** - Concrete declarations:
```
Group G, H
Homomorphism phi := MakeHomomorphism(G, H)
Isomorphism(phi)
```

3. **Style (.style)** - Visual representation with constraints:
```
forall Group g {
  g.icon = Circle { strokeWidth: 2 }
  g.label = Equation { string: g.label }
  ensure contains(g.icon, g.label)
}

forall Homomorphism h
where Isomorphism(h) {
  h.icon = Line {
    start: dom(h).icon.center
    end: cod(h).icon.center
    strokeStyle: "solid"
  }
  -- Double arrow for isomorphism
  h.arrow1 = Line { ... }
  h.arrow2 = Line { ... }
}
```

**CLI workflow:**
```bash
# Install roger CLI
bun add -g @penrose/roger

# Method 1: Direct trio rendering
roger trio trio.json > output.svg

# Method 2: Compile then render (for debugging)
roger compile --trio trio.json -o state.json
roger render state.json -o output.svg
```

**trio.json structure:**
```json
{
  "domain": "./algebra.domain",
  "substance": "./isomorphism.substance",
  "style": ["./algebra.style"],
  "variation": "seed-42"
}
```

**Best use cases:**
- Group theory diagrams (homomorphisms, kernels, images)
- Category theory (commutative diagrams, functors)
- Set theory (Venn diagrams, containment)
- Linear algebra (vector spaces, linear maps)
- Graph theory (automatic node layout)

**Key insight:** Penrose uses constraint-based optimization. You declare *what* relationships should hold (contains, disjoint, near), and the optimizer finds positions. This is powerful for mathematical diagrams where you care about logical relationships, not exact coordinates.

### Tool Selection Decision Tree

```
Need diagram?
├─ Is it a software architecture/system diagram?
│  └─ Use D2 (best for boxes-and-arrows, ERDs)
├─ Is it a mathematical/abstract algebra diagram?
│  ├─ Need automatic layout from math notation?
│  │  └─ Use Penrose (constraint-based)
│  └─ Need precise control over positions?
│     └─ Use TikZ (explicit coordinates)
├─ Is it a 3D visualization?
│  └─ Use Asymptote (native 3D support)
├─ Is it integrated with a Typst document?
│  └─ Use CeTZ (native Typst)
└─ Complex diagram with existing TikZ code?
   └─ Use TikZ (largest ecosystem)
```

## Scripts Reference

### generate.sh
Universal generation script - auto-detects format:
```bash
./scripts/generate.sh FILE [FORMAT] [OPTIONS]

# Examples:
./scripts/generate.sh diagram.typ pdf
./scripts/generate.sh plot.asy svg --no-view
./scripts/generate.sh sets.trio.json
./scripts/generate.sh circuit.tikz.tex
```

### batch-generate.sh
Process all diagrams in a directory:
```bash
./scripts/batch-generate.sh DIRECTORY [FORMAT]

# Example:
./scripts/batch-generate.sh ./paper-figures/ pdf
```

### preview.sh
Live preview with auto-reload:
```bash
./scripts/preview.sh FILE

# Supports: .typ, .asy (with polling)
```

### convert.sh
Convert between formats:
```bash
./scripts/convert.sh INPUT.svg OUTPUT.pdf
./scripts/convert.sh INPUT.pdf OUTPUT.png --dpi 300
```

### check-tools.sh
Verify all tools are installed:
```bash
./scripts/check-tools.sh
```

### D2-specific Scripts

#### d2-validate.sh
Validate D2 diagram syntax:
```bash
./scripts/d2-validate.sh diagram.d2

# Validate multiple files
./scripts/d2-validate.sh *.d2
```

#### d2-check-overlaps.sh
Detect overlapping labels in D2 SVG output:
```bash
# Check with default threshold (20px)
./scripts/d2-check-overlaps.sh diagram.svg

# Check with custom threshold
./scripts/d2-check-overlaps.sh diagram.svg 15

# Example output:
# OVERLAP: "intent" (y=-5.0) and "revise" (y=-5.0)
#   Distance: 0px (threshold: 20px)
```

**Typical workflow:**
```bash
# 1. Generate SVG
d2 --layout elk diagram.d2 diagram.svg

# 2. Check for overlaps
./scripts/d2-check-overlaps.sh diagram.svg

# 3. If overlaps found, view the SVG to identify labels
grep -n "intent\|revise" diagram.svg
```

#### d2-fix-overlap.sh
Fix overlapping label by adjusting position:
```bash
./scripts/d2-fix-overlap.sh input.svg output.svg "label" "old_y" "new_y"

# Example: Move "revise" label up
./scripts/d2-fix-overlap.sh \
  diagram.svg \
  diagram-fixed.svg \
  "revise" \
  "-5.000000" \
  "-32.000000"

# Convert back to PNG
convert -density 150 -background white diagram-fixed.svg diagram-fixed.png
```

**Complete debugging workflow:**
```bash
# 1. Try both layout engines
d2 diagram.d2 diagram-dagre.png
d2 --layout elk diagram.d2 diagram-elk.png

# 2. If overlaps exist, generate SVG for inspection
d2 --layout elk diagram.d2 diagram.svg

# 3. Check for overlaps automatically
./scripts/d2-check-overlaps.sh diagram.svg

# 4. If found, find exact coordinates
grep '<text.*>intent</text>' diagram.svg
grep '<text.*>revise</text>' diagram.svg

# 5. Fix the overlap
./scripts/d2-fix-overlap.sh diagram.svg diagram-fixed.svg "revise" "-5.0" "-32.0"

# 6. Verify fix
./scripts/d2-check-overlaps.sh diagram-fixed.svg

# 7. Convert to final format
convert -density 150 diagram-fixed.svg diagram-fixed.png
```

#### d2-fix.sh
General D2 debugging helper - tests different layouts, analyzes diagram:
```bash
./scripts/d2-fix.sh diagram.d2

# Generates:
# - diagram-dagre.svg
# - diagram-elk.svg
# - Analysis output showing node counts, connection counts, etc.
```

## Advanced Workflows

### CI/CD Integration

```yaml
# .github/workflows/generate-figures.yml
name: Generate Figures
on: [push]
jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: typst-community/setup-typst@v4
      - uses: oven-sh/setup-bun@v1

      - name: Install dependencies
        run: |
          sudo apt-get install -y asymptote
          cd skills/scientific-drawing && bun install

      - name: Generate all figures
        run: ./skills/scientific-drawing/scripts/batch-generate.sh figures/

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: figures
          path: figures/*.pdf
```

### Makefile Integration

```makefile
# Automatic figure generation
TYPST_FIGS := $(wildcard figures/*.typ)
ASY_FIGS := $(wildcard figures/*.asy)
PENROSE_FIGS := $(wildcard figures/*.trio.json)

PDFS := $(TYPST_FIGS:.typ=.pdf) $(ASY_FIGS:.asy=.pdf)
SVGS := $(PENROSE_FIGS:.trio.json=.svg)

all: $(PDFS) $(SVGS)

%.pdf: %.typ
	typst compile $< $@

%.pdf: %.asy
	asy -f pdf -noV $<

%.svg: %.trio.json
	bunx @penrose/roger trio $< > $@

clean:
	rm -f $(PDFS) $(SVGS)

.PHONY: all clean
```

### Reproducible Builds

```bash
# Typst: Fixed timestamps and fonts
typst compile \
  --ignore-system-fonts \
  --font-path ./fonts \
  --creation-timestamp $(git log -1 --format=%ct) \
  diagram.typ

# Asymptote: Configured output
asy -f pdf -noV -render 8 diagram.asy

# Penrose: Fixed variation seed
# In trio.json: "variation": "fixed-seed-123"
```

### Docker Usage

```dockerfile
FROM ubuntu:24.04

# Install all tools
RUN apt-get update && apt-get install -y \
    curl \
    asymptote \
    && curl -fsSL https://typst.app/install.sh | sh

# Install bun
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.bun/bin:$PATH"

WORKDIR /work
COPY package.json bun.lock ./
RUN bun install

# Generate diagrams
CMD ["./scripts/batch-generate.sh", "/work/diagrams/"]
```

## Common Patterns

### Mathematical Notation

**Typst:**
```typst
$ f(x) = sum_(i=0)^n a_i x^i $
```

**Asymptote:**
```asymptote
label("$\\sum_{i=0}^n a_i x^i$", (0,0));
```

**TikZ:**
```tex
\\node at (0,0) {$\\sum_{i=0}^n a_i x^i$};
```

### Data Visualization

**From CSV (Typst):**
```typst
#let data = csv("data.csv")
#import "@preview/cetz:0.2.2": canvas, plot

#canvas({
  plot.plot({
    plot.add(data.map(row => (
      float(row.at(0)),
      float(row.at(1))
    )))
  })
})
```

**From Arrays (Asymptote):**
```asymptote
import graph;
real[] x = {0, 1, 2, 3, 4};
real[] y = {0, 1, 4, 9, 16};
draw(graph(x, y), red);
```

### Export Formats

```bash
# PDF (publication quality)
./scripts/generate.sh diagram.typ pdf
./scripts/generate.sh diagram.asy pdf

# SVG (web, editing)
./scripts/generate.sh diagram.typ svg
./scripts/generate.sh diagram.trio.json  # Always SVG

# PNG (raster, presentations)
./scripts/generate.sh diagram.typ png --ppi 300
./scripts/generate.sh diagram.asy png --dpi 300

# Multiple formats
./scripts/generate.sh diagram.typ pdf,svg,png
```

## Templates

See [templates/](templates/) for:
- `paper-figure.typ` - Scientific paper figure template
- `3d-plot.asy` - 3D visualization template
- `set-theory.trio.json` - Penrose diagram template
- `flowchart.tikz.tex` - TikZ flowchart template
- `neural-network.tikz.tex` - Neural network diagram
- `circuit.tikz.tex` - Circuit diagram

## Testing

Run the test suite:
```bash
cd scripts
bun test
```

Tests verify:
- Tool installations
- Basic compilation for each format
- Helper script functionality
- Format conversions
- Error handling

## Troubleshooting

### Typst compilation fails

```bash
# Check installation
typst --version

# Verify CeTZ package
typst fonts  # Should show available fonts
```

### Asymptote won't run headless

```bash
# Build with offscreen support
./configure --enable-offscreen
make
sudo make install

# Or configure for batch mode
echo 'import settings; settings.interactiveView=false; settings.batchView=false;' > ~/.asy/config.asy
```

### Penrose optimization fails

Try different variation seeds or simplify constraints:
```json
{
  "variation": "try-different-seed"
}
```

### Node/Bun dependencies

```bash
# Reinstall
rm -rf node_modules bun.lock
bun install
```

## Best Practices

1. **Choose the right tool** - Use the tool selection guide above
2. **Version control sources** - Commit `.typ`, `.asy`, `.trio.json`, not PDFs
3. **Automate generation** - Use Makefiles or scripts in CI/CD
4. **Use templates** - Start from templates directory
5. **Reproducible builds** - Fix timestamps, fonts, seeds
6. **Separate content from style** - Especially with Penrose
7. **Test across platforms** - Use Docker for consistency
8. **Cache when possible** - Only regenerate changed diagrams

## Real-World Examples

### Example 1: Conference Paper Figures

```bash
# Generate all paper figures
./scripts/batch-generate.sh paper-figures/ pdf

# Individual figures
./scripts/generate.sh paper-figures/architecture.typ pdf
./scripts/generate.sh paper-figures/results-3d.asy pdf
./scripts/generate.sh paper-figures/category-diagram.trio.json
```

### Example 2: Interactive Documentation

```bash
# Generate SVGs for web
./scripts/batch-generate.sh docs/diagrams/ svg

# Embed in HTML
cat docs/index.html
```

### Example 3: Presentation Slides

```bash
# High-resolution PNGs
./scripts/generate.sh slides/diagram1.typ png --ppi 300
./scripts/generate.sh slides/diagram2.asy png --dpi 300
```

## References

### Documentation
- [Typst Documentation](https://typst.app/docs/)
- [CeTZ Package](https://typst.app/universe/package/cetz/)
- [Asymptote Documentation](https://asymptote.sourceforge.io/)
- [Asymptote Gallery](https://asymptote.sourceforge.io/gallery/)
- [Penrose Documentation](https://penrose.cs.cmu.edu/docs/)
- [Penrose Examples](https://github.com/penrose/penrose/tree/main/packages/examples)
- [TikZ & PGF Manual](https://tikz.dev/)
- [node-tikzjax](https://www.npmjs.com/package/node-tikzjax)

### Example Galleries
- [CeTZ Examples](https://github.com/johannes-wolf/cetz/tree/master/gallery)
- [Asymptote Gallery](http://asymptote.sourceforge.net/gallery/)
- [Penrose Registry](https://github.com/penrose/penrose/tree/main/packages/examples/src)
- [TikZ Examples](https://tikz.net/)

### Community
- [Typst Discord](https://discord.gg/typst)
- [Asymptote Forum](https://sourceforge.net/p/asymptote/discussion/)
- [Penrose GitHub Discussions](https://github.com/penrose/penrose/discussions)
