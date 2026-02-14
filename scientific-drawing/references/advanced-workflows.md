# Advanced Workflows

Batch processing, CI/CD, Docker, and Makefile integration for diagram generation.

## Helper Scripts

```bash
# Auto-detect format and compile
./scripts/generate.sh input.typ          # Typst/CeTZ
./scripts/generate.sh input.asy          # Asymptote
./scripts/generate.sh input.trio.json    # Penrose
./scripts/generate.sh input.tikz.tex     # TikZ
./scripts/generate.sh input.d2           # D2

# Specify format
./scripts/generate.sh input.typ pdf
./scripts/generate.sh input.d2 svg -t 101

# Batch process directory
./scripts/batch-generate.sh ./diagrams/

# Live preview
./scripts/preview.sh input.typ
```

## Makefile Integration

```makefile
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
```

## CI/CD

```yaml
name: Generate Figures
on: [push]
jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: typst-community/setup-typst@v4
      - uses: oven-sh/setup-bun@v1
      - run: sudo apt-get install -y asymptote
      - run: bun install
      - run: ./scripts/batch-generate.sh figures/
      - uses: actions/upload-artifact@v4
        with:
          name: figures
          path: figures/*.pdf
```

## Docker

```dockerfile
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y curl asymptote \
    && curl -fsSL https://typst.app/install.sh | sh
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.bun/bin:$PATH"
WORKDIR /work
COPY package.json bun.lock ./
RUN bun install
CMD ["./scripts/batch-generate.sh", "/work/diagrams/"]
```

## Reproducible Builds

```bash
# Typst: fixed timestamps and fonts
typst compile --ignore-system-fonts --font-path ./fonts \
  --creation-timestamp $(git log -1 --format=%ct) diagram.typ

# Asymptote: configured output
asy -f pdf -noV -render 8 diagram.asy

# Penrose: fixed variation seed
# In trio.json: "variation": "fixed-seed-123"
```

## Best Practices

1. Version control sources (`.typ`, `.asy`, `.trio.json`), not output (PDF/PNG)
2. Automate generation via Makefile or CI
3. Fix timestamps and seeds for reproducibility
4. Cache output — only regenerate changed diagrams
