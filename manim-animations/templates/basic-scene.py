"""Basic Manim scene template

Demonstrates:
- Text creation and animation
- Basic shapes
- Simple animations

Usage:
  uvx manim -pql basic-scene.py BasicScene
  uv run manim -pql basic-scene.py BasicScene
"""

from manim import *


class BasicScene(Scene):
    def construct(self):
        # Create title
        title = Text("My Animation")
        title.to_edge(UP)

        # Create shape
        circle = Circle(radius=1, color=BLUE)

        # Animate
        self.play(Write(title))
        self.play(Create(circle))
        self.play(circle.animate.set_fill(BLUE, opacity=0.5))
        self.wait()
