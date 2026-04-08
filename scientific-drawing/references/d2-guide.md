# D2 Diagramming Reference

Full reference for D2 (v0.7+). For basic usage, see SKILL.md.

## Layout Engines

```bash
d2 input.d2 output.svg                   # dagre (default)
d2 --layout=elk input.d2 output.svg      # Better vertical alignment
d2 --layout=tala input.d2 output.svg     # Best features (Pro license)
```

**When to use which:**
- Dagre: simple hierarchies, quick output
- ELK: complex vertical flows, respects explicit dimensions
- TALA: architecture diagrams with many features

## Rich Content

### Markdown labels
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

### SQL Tables
```d2
users: {
  shape: sql_table
  id: int {constraint: primary_key}
  email: varchar(255) {constraint: unique}
  created_at: timestamp
}
```

### Icons on connections
```d2
server -> client: {
  icon: https://icons.terrastruct.com/essentials/072-network.svg
}
```

### Legends
```d2
legend: {
  critical: {style.fill: red}
  warning: {style.fill: yellow}
  ok: {style.fill: green}
}
```

### Reusable templates
```d2
suspend: true
template_node: { style.fill: blue; style.stroke: black }
unsuspend

node1: @template_node
node2: @template_node
```

## Themes

```bash
d2 themes              # List available
d2 -t 101 in.d2 out.svg  # Grape Soda
d2 -t 200 in.d2 out.svg  # Terminal
```

## Information Design Patterns

### Compact layouts
```d2
GoalRoot: {
  label: "GOAL ROOT"
  width: 420; height: 60    # Explicit dims reduce padding
}

Memories: {
  direction: right           # Horizontal groupings save space
  PrefGraph: {label: "PREF\nGRAPH"; width: 120; height: 70}
  Knowledge: {label: "KNOWLEDGE"; width: 120; height: 70}
}
```

### Semantic color coding
```d2
A -> B: intent     { style.stroke: "#2b6cb0"; style.stroke-width: 2 }   # Blue: top-down
B -> C: forward    { style.stroke: "#2f855a"; style.stroke-dash: 3 }    # Green: data flow
C -> A: feedback   { style.stroke: "#c05621"; style.stroke-dash: 3 }    # Orange: repair
D -> A: conflict   { style.stroke: "#b91c1c"; style.stroke-dash: 5 }    # Red: escalation
A -> Log: log      { style.stroke: "#9ca3af"; style.opacity: 0.4 }      # Gray: de-emphasized
```

### Global styles
```d2
direction: down
*.style.border-radius: 4
*.style.stroke: "#1f2937"
*.style.fill: "#ffffff"
*.style.stroke-width: 1
*.style.font-size: 13
```

### Padding control
```bash
d2 --pad 10 input.d2 output.svg     # Tight padding
d2 --width 750 input.d2 output.png  # Force width
```

## Cyclic Graphs (Feedback Loops)

Backward edges confuse layout. Use `near` constraints:

```d2
TopNode: { near: top-center }      # Pin to top despite incoming edges
BottomNode: { near: bottom-center }

TopNode -> MiddleNode: forward
MiddleNode -> BottomNode: forward
BottomNode -> TopNode: feedback     # Won't pull TopNode down
```

## Debugging Overlapping Labels

1. **Try different layout engines** — ELK often handles complex flows better
2. **Generate SVG** and inspect text positions:
   ```bash
   d2 --layout elk input.d2 output.svg
   grep '<text' output.svg  # Check x/y coordinates for overlaps
   ```
3. **Last resort** — manually adjust SVG coordinates:
   ```bash
   sed 's/y="-5.000000"\(.*>revise\)/y="-32.000000"\1/' input.svg > fixed.svg
   ```

## Validation

```bash
d2 validate input.d2     # Syntax check before rendering
d2 --watch input.d2 out.svg  # Live preview
```

## Reference

- D2 source and examples: `~/Projects/best/d2`
- [D2 documentation](https://d2lang.com/)
