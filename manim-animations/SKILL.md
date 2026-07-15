---
name: manim-animations
description: "Use when: Manim/3B1B-style math animation, equation visuals, render manim scenes. NOT static figures (/scientific-drawing)."
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# Manim Mathematical Animations

Create high-quality mathematical animations using Manim, the Python library created by Grant Sanderson (3Blue1Brown) for programmatic animations.

## Prerequisites

### Installation

Manim requires Python 3.10+ and system dependencies including LaTeX.

**System dependencies (macOS):**
```bash
brew install py3cairo ffmpeg
brew install --cask mactex-no-gui  # For LaTeX rendering
```

**Three ways to use Manim:**

#### 1. Project-based with uv (Recommended for development)
```bash
# In your project directory
cd ~/Projects/manimations
uv sync  # Installs manim from pyproject.toml

# Run manim via uv
uv run manim -pql myfile.py MyScene
```

#### 2. Global tool with uvx (Recommended for one-off animations)
```bash
# Run without installing
uvx manim -pql myfile.py MyScene

# Or install as global tool
uv tool install manim

# Then use directly
manim -pql myfile.py MyScene
```

#### 3. Quick edits with uvx --with flag
```bash
# Use additional packages in one command
uvx --with manim --with numpy python myanimation.py

# Or edit/create files with dependencies available
uvx --with manim --python python3.11 --edit myfile.py
```

**Verify installation:**
```bash
# Check manim
manim --version

# Or via uvx
uvx manim --version

# Check system dependencies
./scripts/check-tools.sh
```

## Quick Start

### Basic Animation Structure

Every Manim animation is a Python class that inherits from `Scene`:

```python
from manim import *

class HelloManim(Scene):
    def construct(self):
        # Create objects
        text = Text("Hello, Manim!")

        # Animate
        self.play(Write(text))
        self.wait()
```

### Rendering Animations

**With uv (in project):**
```bash
# Preview quality (fast, 480p15)
uv run manim -pql hello.py HelloManim

# Low quality (854x480, 15fps)
uv run manim -ql hello.py HelloManim

# Medium quality (1280x720, 30fps)
uv run manim -qm hello.py HelloManim

# High quality (1920x1080, 60fps)
uv run manim -qh hello.py HelloManim

# Production quality (3840x2160, 60fps, 4K)
uv run manim -qk hello.py HelloManim
```

**With uvx (anywhere):**
```bash
# One-off render without installation
uvx manim -pql hello.py HelloManim

# Custom resolution and framerate
uvx manim -r 1920,1080 --frame_rate 24 hello.py HelloManim

# With additional packages
uvx --with manim --with scipy manim -pql physics.py PhysicsScene
```

**Quality flags:**
- `-pql`: Preview (low quality) and play immediately
- `-p`: Play video after rendering
- `-ql`: Low quality (fast iteration)
- `-qm`: Medium quality (balanced)
- `-qh`: High quality (presentation)
- `-qk`: 4K quality (production)

### Helper Scripts

These scripts automatically use `uv run` when in a project with `pyproject.toml`:

```bash
# Render animation (auto-opens)
./scripts/render.sh hello.py HelloManim

# Preview with live reload
./scripts/preview.sh hello.py HelloManim

# Render all scenes in a file
./scripts/render-all.sh hello.py

# Batch render directory
./scripts/batch-render.sh ./animations/
```

## Planning a Complex Explainer (reverse reasoning)

For anything beyond a single effect — a multi-scene explainer of a real concept —
don't jump from prompt to Python. Reason *backward* from the target idea to its
prerequisites, then walk *forward* through a teachable visual order. This is the
core idea behind HarleyCoops/Math-To-Manim, and it's why its output is
pedagogically coherent instead of a pile of animations. Plan these in order before
writing any `Scene`:

1. **Intent** — what is the learner actually asking? Pin the one idea the video
   must land.
2. **Prerequisites** — what must they already understand for that idea to make
   sense? Build the dependency list backward from the target.
3. **Order (curriculum)** — sequence the prerequisites into a teachable path:
   intuition → concrete example → formal statement.
4. **Math packet** — pick the specific definitions, equations, and one worked
   example. Prefer the sparsest notation that's still honest.
5. **Storyboard** — decide the on-screen beats (what appears, transforms, leaves)
   *before* code. One beat per idea.
6. **Scene spec → code** — only now map beats to mobjects, animations, timing, and
   camera moves.

Guiding principle: **story before symbols, geometry before algebra, artifacts
before side effects.** Keep formulas sparse, captions staged (reveal one at a
time), and each scene built around a single beat. For a fully automated version of
this pipeline (intent → prerequisite graph → storyboard → codegen → render →
repair, each a typed artifact), see that repo — but for hand-authoring, the
ordered plan above is the takeaway.

## Core Concepts

### 1. Mobjects (Mathematical Objects)

Everything in Manim is a `Mobject`:

```python
from manim import *

class MobjectDemo(Scene):
    def construct(self):
        # Text
        title = Text("Mobjects")

        # Math equations (LaTeX)
        equation = MathTex(r"e^{i\pi} + 1 = 0")

        # Geometric shapes
        circle = Circle(radius=1, color=BLUE)
        square = Square(side_length=2, color=RED)

        # Position objects
        title.to_edge(UP)
        equation.next_to(title, DOWN)

        # Animate
        self.play(Write(title))
        self.play(Write(equation))
        self.play(Create(circle), Create(square))
        self.wait()
```

### 2. Animations

Manim provides rich animation primitives:

```python
class AnimationDemo(Scene):
    def construct(self):
        square = Square()

        # Creation animations
        self.play(Create(square))          # Draw shape
        self.play(FadeIn(square))          # Fade in
        self.play(Write(square))           # Write text/shape

        # Transformation animations
        self.play(Transform(square, Circle()))  # Morph
        self.play(ReplacementTransform(square, Circle()))  # Replace

        # Movement animations
        self.play(square.animate.shift(RIGHT * 2))
        self.play(square.animate.rotate(PI / 4))
        self.play(square.animate.scale(2))

        # Opacity and color
        self.play(square.animate.set_opacity(0.5))
        self.play(square.animate.set_color(RED))

        # Removal
        self.play(FadeOut(square))
        self.play(Uncreate(square))
```

### 3. Mathematical Expressions

Manim excels at mathematical typesetting using LaTeX:

```python
class MathDemo(Scene):
    def construct(self):
        # Simple equation
        eq1 = MathTex(r"f(x) = x^2")

        # Multi-line equations
        eq2 = MathTex(
            r"\int_0^\infty e^{-x^2} dx",
            r"=",
            r"\frac{\sqrt{\pi}}{2}"
        )

        # Color specific parts
        eq3 = MathTex(
            r"\nabla \times \mathbf{E}",
            r"= -\frac{\partial \mathbf{B}}{\partial t}"
        )
        eq3[0].set_color(BLUE)  # Color the curl
        eq3[1].set_color(RED)   # Color the derivative

        # Transforming equations
        self.play(Write(eq1))
        self.wait()
        self.play(TransformMatchingTex(eq1, eq2))
        self.wait()
```

### 4. Graphs and Plots

```python
class GraphDemo(Scene):
    def construct(self):
        # Create axes
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            x_length=6,
            y_length=6,
            axis_config={"include_tip": True}
        )

        # Add labels
        labels = axes.get_axis_labels(x_label="x", y_label="f(x)")

        # Plot function
        graph = axes.plot(lambda x: x**2, color=BLUE)
        graph_label = axes.get_graph_label(graph, label="x^2")

        # Animate
        self.play(Create(axes), Write(labels))
        self.play(Create(graph), Write(graph_label))
        self.wait()
```

### 5. Camera Movement

```python
class CameraDemo(MovingCameraScene):
    def construct(self):
        square = Square()

        self.play(Create(square))

        # Zoom in
        self.play(self.camera.frame.animate.scale(0.5))

        # Move camera
        self.play(self.camera.frame.animate.shift(RIGHT * 2))

        # Zoom out
        self.play(self.camera.frame.animate.scale(2))

        self.wait()
```

### 6. 3D Scenes

```python
class ThreeDDemo(ThreeDScene):
    def construct(self):
        # 3D axes
        axes = ThreeDAxes()

        # 3D surface
        surface = Surface(
            lambda u, v: axes.c2p(u, v, u**2 + v**2),
            u_range=[-2, 2],
            v_range=[-2, 2],
            resolution=(20, 20)
        )

        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES)
        self.play(Create(axes))
        self.play(Create(surface))

        # Rotate camera
        self.begin_ambient_camera_rotation(rate=0.2)
        self.wait(5)
        self.stop_ambient_camera_rotation()
```

## Common Animation Patterns

### Highlighting and Focus

```python
class HighlightDemo(Scene):
    def construct(self):
        equation = MathTex(r"a^2 + b^2 = c^2")

        # Indicate (temporary highlight)
        self.play(Indicate(equation[0]))  # Highlight a^2

        # Circumscribe (draw attention)
        self.play(Circumscribe(equation[4], color=RED))  # Circle c^2

        # Flash
        self.play(Flash(equation[2]))  # Flash the equals sign

        # Wiggle
        self.play(Wiggle(equation))
```

### Step-by-Step Derivations

```python
class DerivationDemo(Scene):
    def construct(self):
        steps = [
            MathTex(r"x^2 - 4 = 0"),
            MathTex(r"x^2 = 4"),
            MathTex(r"x = \pm 2")
        ]

        # Position all at same location
        for step in steps:
            step.move_to(ORIGIN)

        # Animate through steps
        self.play(Write(steps[0]))
        self.wait()

        for i in range(len(steps) - 1):
            self.play(TransformMatchingTex(steps[i], steps[i + 1]))
            self.wait()
```

### Function Transformations

```python
class TransformGraphDemo(Scene):
    def construct(self):
        axes = Axes(x_range=[-3, 3], y_range=[-3, 3])

        # Original function
        f1 = axes.plot(lambda x: x**2, color=BLUE)
        label1 = MathTex(r"f(x) = x^2").to_edge(UP)

        # Transformed function
        f2 = axes.plot(lambda x: -(x**2), color=RED)
        label2 = MathTex(r"f(x) = -x^2").to_edge(UP)

        self.play(Create(axes))
        self.play(Create(f1), Write(label1))
        self.wait()

        self.play(
            Transform(f1, f2),
            TransformMatchingTex(label1, label2)
        )
        self.wait()
```

### Vector Fields

```python
class VectorFieldDemo(Scene):
    def construct(self):
        # Define vector field function
        def field_func(pos):
            x, y = pos[:2]
            return np.array([y, -x, 0])

        # Create vector field
        field = ArrowVectorField(field_func)

        # Animate
        self.play(Create(field))
        self.wait()
```

## Advanced Techniques

### Custom Animations

```python
class CustomAnimationDemo(Scene):
    def construct(self):
        square = Square()

        # Custom rate function
        self.play(
            square.animate.shift(RIGHT * 3),
            rate_func=there_and_back,  # Goes right then back
            run_time=2
        )

        # Combine animations with different timings
        self.play(
            square.animate.rotate(PI),
            square.animate.set_color(RED),
            run_time=1.5
        )
```

### Updaters

```python
class UpdaterDemo(Scene):
    def construct(self):
        square = Square()
        label = Text("Square")

        # Label follows square
        label.add_updater(lambda m: m.next_to(square, UP))

        self.add(square, label)
        self.play(square.animate.shift(RIGHT * 3))
        self.play(square.animate.shift(UP * 2))

        label.clear_updaters()
```

### Value Trackers

```python
class ValueTrackerDemo(Scene):
    def construct(self):
        tracker = ValueTracker(0)

        # Create number that updates
        number = DecimalNumber(0)
        number.add_updater(lambda m: m.set_value(tracker.get_value()))

        # Create shape that scales with tracker
        circle = Circle()
        circle.add_updater(
            lambda m: m.set_width(2 * tracker.get_value() + 0.1)
        )

        self.add(number.to_edge(UP), circle)
        self.play(tracker.animate.set_value(3), run_time=3)
```

### LaTeX Templates

Customize LaTeX rendering:

```python
class CustomLatexDemo(Scene):
    def construct(self):
        # Use specific LaTeX packages
        myTemplate = TexTemplate()
        myTemplate.add_to_preamble(r"\usepackage{mathrsfs}")

        equation = MathTex(
            r"\mathscr{L}",
            tex_template=myTemplate
        )

        self.play(Write(equation))
```

## Templates and Examples

### Template 1: Educational Explanation

```python
from manim import *

class ConceptExplanation(Scene):
    def construct(self):
        # Title
        title = Text("The Pythagorean Theorem")
        title.to_edge(UP)
        self.play(Write(title))
        self.wait()

        # Create right triangle
        triangle = Polygon(
            ORIGIN, RIGHT * 3, RIGHT * 3 + UP * 2,
            color=WHITE
        )

        # Label sides
        a_label = MathTex("a").next_to(triangle, DOWN)
        b_label = MathTex("b").next_to(triangle, RIGHT)
        c_label = MathTex("c").move_to(triangle.get_center() + LEFT * 0.5)

        self.play(Create(triangle))
        self.play(Write(a_label), Write(b_label), Write(c_label))
        self.wait()

        # Show equation
        equation = MathTex(r"a^2 + b^2 = c^2")
        equation.next_to(triangle, LEFT, buff=1)

        self.play(Write(equation))
        self.wait(2)
```

### Template 2: Algorithm Visualization

```python
from manim import *

class BubbleSortVisualization(Scene):
    def construct(self):
        # Title
        title = Text("Bubble Sort")
        title.to_edge(UP)
        self.play(Write(title))

        # Create array
        values = [5, 2, 8, 1, 9]
        bars = VGroup(*[
            Rectangle(height=v*0.5, width=0.8, fill_opacity=0.8)
            for v in values
        ])
        bars.arrange(RIGHT, buff=0.2)

        # Add labels
        labels = VGroup(*[
            Text(str(v), font_size=24).next_to(bar, DOWN)
            for v, bar in zip(values, bars)
        ])

        self.play(Create(bars), Write(labels))
        self.wait()

        # Sorting animation (simplified)
        # ... implement bubble sort swaps with animations ...
```

### Template 3: Function Visualization

```python
from manim import *

class FunctionVisualization(Scene):
    def construct(self):
        # Setup axes
        axes = Axes(
            x_range=[-5, 5, 1],
            y_range=[-3, 3, 1],
            x_length=10,
            y_length=6,
            axis_config={
                "include_tip": True,
                "numbers_to_include": range(-5, 6)
            }
        )

        labels = axes.get_axis_labels(x_label="x", y_label="y")

        # Function
        graph = axes.plot(lambda x: np.sin(x), color=BLUE)
        graph_label = axes.get_graph_label(
            graph,
            label=MathTex(r"y = \sin(x)"),
            x_val=3,
            direction=UP
        )

        # Animate
        self.play(Create(axes), Write(labels))
        self.play(Create(graph), Write(graph_label))

        # Show specific point
        dot = Dot(axes.c2p(PI/2, 1), color=RED)
        self.play(Create(dot))
        self.wait()
```

### Template 4: 3D Visualization

```python
from manim import *

class ThreeDVisualization(ThreeDScene):
    def construct(self):
        # Setup 3D axes
        axes = ThreeDAxes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            z_range=[-3, 3, 1]
        )

        # Create 3D object
        sphere = Sphere(radius=1, color=BLUE)

        # Set camera
        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES)

        # Animate
        self.play(Create(axes))
        self.play(Create(sphere))

        # Rotate camera around object
        self.begin_ambient_camera_rotation(rate=0.3)
        self.wait(5)
        self.stop_ambient_camera_rotation()
```

## Workflow Best Practices

### 1. Project Structure

```
project/
├── animations/
│   ├── intro.py
│   ├── chapter1.py
│   └── chapter2.py
├── assets/
│   ├── images/
│   └── audio/
├── media/          # Auto-generated by Manim
│   ├── videos/
│   └── images/
└── pyproject.toml
```

### 2. Development Workflow

```bash
# 1. Quick iteration with preview quality
manim -pql myfile.py MyScene

# 2. Test at medium quality
manim -qm myfile.py MyScene

# 3. Final render at high quality
manim -qh myfile.py MyScene

# 4. Production render (4K)
manim -qk myfile.py MyScene
```

### 3. Configuration

Create `manim.cfg` in your project:

```ini
[CLI]
quality = high_quality
preview = True
output_file = custom_name

[output]
video_dir = {media_dir}/videos/{module_name}/{quality}
images_dir = {media_dir}/images/{module_name}
```

### 4. Scene Selection

```bash
# List all scenes in file
manim myfile.py --scene_names

# Render specific scenes
manim myfile.py Scene1 Scene2

# Render all scenes
manim -a myfile.py
```

### 5. Rendering Options

```bash
# Save last frame as image
manim -sql myfile.py MyScene

# Transparent background
manim -t myfile.py MyScene

# GIF output
manim --format gif myfile.py MyScene

# Custom background color
manim -c "#2B2B2B" myfile.py MyScene

# Render sections only
manim --from_animation_number 5 --to_animation_number 10 myfile.py MyScene
```

## Performance Optimization

### Caching

Manim caches rendered objects to speed up iterations:

```python
class CachedDemo(Scene):
    def construct(self):
        # Complex object that's slow to render
        complex_tex = MathTex(
            r"\int_0^\infty \frac{\sin(x)}{x} dx = \frac{\pi}{2}"
        )
        # Manim automatically caches this between runs

        self.play(Write(complex_tex))
```

Clear cache when needed:
```bash
# Clear all cached files
manim --flush_cache myfile.py MyScene
```

### Render Sections

Use sections for faster iteration on specific parts:

```python
class SectionDemo(Scene):
    def construct(self):
        # Section 1
        self.next_section("Introduction")
        title = Text("Introduction")
        self.play(Write(title))

        # Section 2
        self.next_section("Main Content", skip_animations=False)
        content = Text("Main content here")
        self.play(Write(content))

        # Section 3
        self.next_section("Conclusion")
        conclusion = Text("Conclusion")
        self.play(Write(conclusion))
```

Render only specific sections:
```bash
manim --save_sections myfile.py MyScene
```

### Rendering at Scale: CPU, Parallelism, and Modal

**Manim is CPU-bound, not GPU-bound.** The default Cairo renderer is a software
rasterizer; ffmpeg encode is also CPU. There is no Metal backend, and the OpenGL
renderer (`--renderer=opengl`) is for interactive preview, not headless batch
output — on macOS it is deprecated GL-on-Metal and fragile. A discrete/integrated
GPU does essentially nothing for normal renders. The lever is **CPU cores**, used
as one process per scene.

**Measured anchors** (Apple M3 Pro, 6 perf + 6 eff cores, 1080p60, cold,
`--disable_caching`, manim 0.19; benchmark 2026-05-30):

| Scene type | render | playback | ratio | threading |
|---|---|---|---|---|
| 2D light | ~4s | 4.0s | ~0.9× | uses ~2 cores |
| 2D, 10 animations | ~7–10s | 14.8s | ~0.7× | uses ~2 cores |
| **3D surface, 16 animations** | **~195–211s** | 18.4s | **~11×** | single-threaded |

Process startup (`import manim`) is ~0.5s — negligible. The headline: **2D scenes
render faster than real-time; a 3D scene renders ~11× slower than real-time and is
single-threaded.** 3D is where time goes.

**Parallelize across cores locally first.** Render scenes as independent processes
(one manim invocation per scene), fanned out across cores. Enumerate the scene
classes per file (parse the AST, don't execute), then drive them through
`xargs -P` / GNU `parallel`:

```bash
# Pseudocode: for each (file, scene) pair, render concurrently
for f in *.py; do
  for s in $(python list_scene_classes.py "$f"); do printf '%s\t%s\n' "$f" "$s"; done
done | xargs -P6 -L1 sh -c 'manim -qh "$0" "$1"'
```

(See the `manimations` project's `tools/render_all.sh` + `make render-all` for a
working implementation of exactly this.) For a single slow 3D scene, split it into
time segments (`--from_animation_number` / `--to_animation_number`) and render the
segments in parallel — the only way to parallelize *within* one scene.

**Gate before you render.** A 3D render can cost minutes; don't spend it on a
script that won't parse or whose scene class doesn't exist. AST-validate first
(parse + scene-class-exists, no execution) and only render on success — the
`manimations` project's `tools/validate_scene.py` does this and `make render`
depends on it. Note: Manim CE has **no** video-codec CLI flag (`-c` is
`--config_file`), and the ffmpeg encode is a small fraction of render time anyway,
so there's no hardware-encode win worth chasing.

**Modal (cloud) — when it actually helps.** Manim renders fan out cleanly (one
container per scene, baked image with cairo/ffmpeg/TeX, `min_containers=0`).
But Modal adds ~25–35s of fixed overhead (container boot + script upload +
download partials + concat) that does not shrink. Net verdict from the measured
numbers above:

- **30s 1080p, 2D:** local serial ~28s, local parallel ~10s, Modal ~30s+.
  Modal is *slower* — do not use it.
- **30s 1080p, ≤6 heavy/3D scenes:** local 6-core parallel ≈ Modal (a wash);
  6 perf cores cover one wave.
- **Modal wins (~1.5–4×) only when:** >6 heavy/3D scenes (local serializes past
  core count), 4K (`-qk`, render ×4 makes overhead negligible), or batch jobs
  (many videos at once / CI offload / avoiding a local TeX install).

Rule of thumb: **render locally with `make -j6` unless you're doing 4K-heavy, many
heavy scenes, or large batches.** The cloud is a net loss at single-explainer scale.

## Troubleshooting

### LaTeX Errors

```bash
# Check LaTeX installation
which latex
pdflatex --version

# Test LaTeX rendering
manim -pql test.py LatexTest --tex_template <template>

# View LaTeX logs
# Check media/Tex/*.log files
```

### Performance Issues

```bash
# Use lower quality for testing
manim -ql myfile.py MyScene

# Disable preview window
manim -q myfile.py MyScene  # No -p flag

# Render at lower framerate
manim --frame_rate 15 myfile.py MyScene
```

### Import Errors

```bash
# Verify Manim installation
python -c "import manim; print(manim.__version__)"

# Reinstall if needed
uv sync --reinstall-package manim
```

### FFmpeg Issues

```bash
# Check FFmpeg
which ffmpeg
ffmpeg -version

# Reinstall if needed (macOS)
brew reinstall ffmpeg
```

## Useful Resources

### Documentation
- [Manim Community Docs](https://docs.manim.community/)
- [Manim Reference Manual](https://docs.manim.community/en/stable/reference.html)
- [Example Gallery](https://docs.manim.community/en/stable/examples.html)

### Video Tutorials
- [3Blue1Brown Channel](https://www.youtube.com/c/3blue1brown) - Original inspiration
- [Theorem of Beethoven](https://www.youtube.com/c/TheoremofBeethoven) - Manim tutorials

### Community
- [Manim Discord](https://discord.gg/mMRrZQW)
- [r/manim](https://reddit.com/r/manim)
- [Manim GitHub](https://github.com/ManimCommunity/manim)

### Color Palettes

Manim includes color constants:
```python
# Basic colors
RED, GREEN, BLUE, YELLOW, PURPLE, ORANGE, PINK, GRAY

# Lighter/darker variants
RED_A, RED_B, RED_C, RED_D, RED_E  # Increasing darkness
LIGHT_GRAY, GRAY, DARK_GRAY

# Custom colors
from manim import rgb_to_color
custom = rgb_to_color([0.5, 0.7, 0.9])
```

## Quick Reference

### Common Animations
```python
# Creation
Create(obj)           # Draw/create object
Write(obj)           # Write text/equation
FadeIn(obj)          # Fade in

# Transformation
Transform(obj1, obj2)              # Morph obj1 into obj2
ReplacementTransform(obj1, obj2)   # Replace obj1 with obj2
TransformMatchingTex(eq1, eq2)     # Smart equation transformation

# Movement
obj.animate.shift(direction)
obj.animate.move_to(point)
obj.animate.rotate(angle)
obj.animate.scale(factor)

# Indication
Indicate(obj)         # Temporary highlight
Circumscribe(obj)     # Circle object
Flash(obj)           # Flash effect
Wiggle(obj)          # Wiggle object

# Removal
FadeOut(obj)         # Fade out
Uncreate(obj)        # Reverse creation
```

### Scene Types
```python
Scene               # Basic 2D scene
MovingCameraScene   # Camera can move/zoom
ThreeDScene         # 3D animations
VectorScene         # Vector-focused scenes
ZoomedScene         # Built-in zooming
```

### Configuration
```bash
# Quality presets
-ql   # Low: 854x480@15fps
-qm   # Medium: 1280x720@30fps
-qh   # High: 1920x1080@60fps
-qk   # 4K: 3840x2160@60fps

# Flags
-p    # Preview (auto-play)
-s    # Save last frame only
-t    # Transparent background
-a    # Render all scenes
```

This skill provides everything needed to create professional mathematical animations with Manim!
