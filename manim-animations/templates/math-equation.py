"""Mathematical equation template

Demonstrates:
- LaTeX math rendering
- Equation transformations
- Step-by-step derivations

Usage:
  uvx manim -pql math-equation.py EquationDemo
"""

from manim import *


class EquationDemo(Scene):
    def construct(self):
        # Title
        title = Text("Quadratic Formula Derivation")
        title.to_edge(UP)
        self.play(Write(title))
        self.wait()

        # Steps of derivation
        steps = [
            MathTex(r"ax^2 + bx + c = 0"),
            MathTex(r"x^2 + \frac{b}{a}x + \frac{c}{a} = 0"),
            MathTex(r"x^2 + \frac{b}{a}x = -\frac{c}{a}"),
            MathTex(r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}"),
        ]

        # Position all steps at center
        for step in steps:
            step.move_to(ORIGIN)

        # Animate through derivation
        self.play(Write(steps[0]))
        self.wait()

        for i in range(len(steps) - 1):
            self.play(TransformMatchingTex(steps[i], steps[i + 1]))
            self.wait()

        self.wait(2)


class ColoredEquation(Scene):
    def construct(self):
        # Create equation with colored parts
        equation = MathTex(
            r"\int_0^\infty",
            r"e^{-x^2}",
            r"dx",
            r"=",
            r"\frac{\sqrt{\pi}}{2}"
        )

        # Color specific parts
        equation[0].set_color(BLUE)    # Integral
        equation[1].set_color(RED)     # Integrand
        equation[2].set_color(BLUE)    # dx
        equation[4].set_color(GREEN)   # Result

        self.play(Write(equation))
        self.wait(2)
