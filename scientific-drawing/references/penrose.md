<!-- Reference file for scientific-drawing skill. Loaded on demand. -->
# Penrose Reference

Three-file architecture: domain (types) + substance (instances) + style (rendering).

## Example

`sets.domain`:
```
type Set
predicate Subset(Set, Set)
```

`diagram.substance`:
```
Set A, B
Subset(A, B)
```

`venn.style`:
```
forall Set x {
  x.shape = Circle { strokeWidth: 2 }
}
forall Set A; Set B where Subset(A, B) {
  ensure contains(B.shape, A.shape)
}
```

`trio.json`:
```json
{
  "domain": "./sets.domain",
  "style": ["./venn.style"],
  "substance": "./diagram.substance",
  "variation": "seed-42"
}
```

## Compile

```bash
bunx @penrose/roger trio trio.json > output.svg
```

## Gotchas

- Constraint-based: declare relationships, optimizer finds positions
- If optimization fails, try different `"variation"` seeds
- Best for: set theory, category theory, graph theory — where logical relationships matter more than exact coordinates
