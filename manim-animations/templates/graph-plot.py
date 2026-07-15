"""Graph and function plotting template

Demonstrates:
- Creating axes
- Plotting functions
- Labels and annotations
- Function transformations

Usage:
  uvx manim -pql graph-plot.py FunctionPlot
  uvx manim -pql graph-plot.py TransformFunction
"""

from manim import *


class FunctionPlot(Scene):
    def construct(self):
        # Create axes
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            x_length=6,
            y_length=6,
            axis_config={
                "include_tip": True,
                "numbers_to_include": range(-3, 4),
            }
        )

        # Add labels
        labels = axes.get_axis_labels(x_label="x", y_label="y")

        # Plot function
        graph = axes.plot(lambda x: x**2, color=BLUE)
        graph_label = axes.get_graph_label(
            graph,
            label=MathTex(r"f(x) = x^2"),
            x_val=2,
            direction=UP
        )

        # Animate
        self.play(Create(axes), Write(labels))
        self.wait()
        self.play(Create(graph), Write(graph_label))
        self.wait()

        # Highlight specific point
        dot = Dot(axes.c2p(1, 1), color=RED)
        dot_label = MathTex(r"(1, 1)").next_to(dot, RIGHT)

        self.play(Create(dot), Write(dot_label))
        self.wait(2)


class TransformFunction(Scene):
    def construct(self):
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            x_length=8,
            y_length=6
        )

        # Original function
        f1 = axes.plot(lambda x: x**2, color=BLUE)
        label1 = MathTex(r"f(x) = x^2").to_edge(UP)

        # Transformed function
        f2 = axes.plot(lambda x: -(x**2), color=RED)
        label2 = MathTex(r"f(x) = -x^2").to_edge(UP)

        self.play(Create(axes))
        self.play(Create(f1), Write(label1))
        self.wait()

        # Transform
        self.play(
            Transform(f1, f2),
            TransformMatchingTex(label1, label2)
        )
        self.wait(2)


class MultipleFunctions(Scene):
    def construct(self):
        axes = Axes(
            x_range=[-5, 5, 1],
            y_range=[-2, 2, 1],
            x_length=10,
            y_length=6
        )

        # Plot multiple functions
        sin_graph = axes.plot(lambda x: np.sin(x), color=BLUE)
        cos_graph = axes.plot(lambda x: np.cos(x), color=RED)

        sin_label = axes.get_graph_label(sin_graph, label=r"\sin(x)", x_val=-4)
        cos_label = axes.get_graph_label(cos_graph, label=r"\cos(x)", x_val=-3)

        self.play(Create(axes))
        self.play(
            Create(sin_graph),
            Create(cos_graph),
            Write(sin_label),
            Write(cos_label)
        )
        self.wait(2)
