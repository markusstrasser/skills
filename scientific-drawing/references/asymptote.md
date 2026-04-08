<!-- Reference file for scientific-drawing skill. Loaded on demand. -->
# Asymptote Reference

## 2D

```asymptote
import graph;
size(200);
draw(unitcircle, blue);
dot((0,0), red);
label("Origin", (0,0), S);
```

## 3D

```asymptote
import graph3;
size(200);
currentprojection=orthographic(4,2,3);
draw(surface((x,y) => x^2+y^2, (-1,-1), (1,1), nx=20, ny=20),
    lightblue+opacity(0.7));
axes3("$x$", "$y$", "$z$");
```

## Compile

```bash
asy -f pdf -noV diagram.asy
asy -f svg -noV diagram.asy
```

## Gotchas

- For headless/batch: `settings.interactiveView=false; settings.batchView=false;` in `~/.asy/config.asy`
- 3D rendering needs OpenGL or `-render 0` for vector output
