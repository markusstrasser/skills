# Manim Examples

Example animations demonstrating various Manim capabilities.

## Templates

Start with these templates in the `templates/` directory:

### Basic Templates
- `basic-scene.py` - Simple shapes and text
- `math-equation.py` - LaTeX equations and transformations
- `graph-plot.py` - Function plotting and graphing
- `3d-scene.py` - 3D objects and camera movement

## Running Examples

```bash
# From project with uv
cd ~/Projects/manimations
uv run manim -pql ../skills/manim-animations/templates/basic-scene.py BasicScene

# With uvx (anywhere)
uvx manim -pql templates/math-equation.py EquationDemo

# High quality render
uvx manim -qh templates/3d-scene.py Surface3D
```

## Quality Levels

- `-pql` - Preview low (fast iteration, 480p@15fps, auto-plays)
- `-ql` - Low (854x480@15fps)
- `-qm` - Medium (1280x720@30fps)
- `-qh` - High (1920x1080@60fps)
- `-qk` - 4K (3840x2160@60fps)

## Common Patterns

### Creating Text
```python
text = Text("Hello")
equation = MathTex(r"E = mc^2")
```

### Basic Animations
```python
self.play(Write(text))        # Write text
self.play(Create(shape))      # Draw shape
self.play(FadeIn(object))     # Fade in
self.play(Transform(a, b))    # Morph a into b
```

### Movement
```python
self.play(object.animate.shift(RIGHT * 2))
self.play(object.animate.rotate(PI / 4))
self.play(object.animate.scale(2))
```

### Colors
```python
shape.set_color(BLUE)
shape.set_fill(RED, opacity=0.5)
```

## Learning Resources

- [Official Manim Docs](https://docs.manim.community/)
- [Example Gallery](https://docs.manim.community/en/stable/examples.html)
- [3Blue1Brown](https://www.youtube.com/c/3blue1brown) - Original creator
