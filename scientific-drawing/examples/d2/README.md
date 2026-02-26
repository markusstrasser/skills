# D2 Examples for Scientific Diagrams

This directory contains D2 examples demonstrating features useful for scientific diagrams, particularly v0.7+ features.

## Examples

### 1. system-architecture.d2
**Purpose:** Scientific computing system architecture

**Features demonstrated:**
- Rich markdown labels with LaTeX math
- Code blocks in labels
- Multiple shapes (cylinder, hexagon, rectangle, page)
- Legend (v0.7 feature)
- Custom styling with colors

**Generate:**
```bash
d2 system-architecture.d2 system-architecture.svg
# or with theme
d2 -t 101 system-architecture.d2 system-architecture.svg
```

### 2. database-schema.d2
**Purpose:** Research database ERD

**Features demonstrated:**
- SQL tables (v0.7 feature)
- Primary key, foreign key, unique constraints
- Automatic constraint abbreviation
- Row-level connections (with TALA/ELK)

**Generate:**
```bash
# Best with TALA layout for SQL tables
d2 --layout=tala database-schema.d2 database-schema.svg

# Or ELK
d2 --layout=elk database-schema.d2 database-schema.svg
```

### 3. experiment-workflow.d2
**Purpose:** Scientific experiment workflow

**Features demonstrated:**
- Containers for grouping
- Multiple shape types
- Conditional flow (dashed arrows)
- Direction control
- Markdown in descriptions

**Generate:**
```bash
d2 experiment-workflow.d2 experiment-workflow.svg
```

## Best Practices for Scientific Diagrams

1. **Use appropriate layouts:**
   - `dagre` (default) - Good for most diagrams
   - `tala` - Best for SQL tables, advanced positioning
   - `elk` - Good for hierarchical structures

2. **Leverage v0.7 features:**
   - Use markdown labels for equations and code
   - Add legends for complex diagrams
   - Use SQL tables for database schemas
   - Add icons to connections when needed

3. **Styling:**
   - Use consistent colors for node types
   - Add legends to explain color coding
   - Use shape variety to distinguish components

4. **Validation:**
   ```bash
   d2 validate your-diagram.d2
   ```

5. **Watch mode during development:**
   ```bash
   d2 --watch your-diagram.d2 output.svg
   ```

## Converting to PDF

```bash
# Generate SVG first
d2 diagram.d2 diagram.svg

# Convert to PDF (requires rsvg-convert or similar)
rsvg-convert -f pdf -o diagram.pdf diagram.svg

# Or use ImageMagick
convert diagram.svg diagram.pdf
```

## Themes for Publications

```bash
# List all themes
d2 themes

# Professional themes for papers:
d2 -t 0 diagram.d2 output.svg    # Neutral (good for papers)
d2 -t 3 diagram.d2 output.svg    # Cool classics
d2 -t 100 diagram.d2 output.svg  # Origami
```

## Reference

- D2 Documentation: https://d2lang.com
- D2 Source: ~/Projects/best/d2
- v0.7 Release Notes: https://d2lang.com/releases/0.7.0
