"""3D visualization template

Demonstrates:
- 3D axes and objects
- Camera positioning
- Camera rotation
- 3D surfaces

Usage:
  uvx manim -pql 3d-scene.py Basic3D
  uvx manim -pql 3d-scene.py Surface3D
"""

from manim import *


class Basic3D(ThreeDScene):
    def construct(self):
        # Set camera position
        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES)

        # Create 3D axes
        axes = ThreeDAxes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            z_range=[-3, 3, 1]
        )

        # Create 3D objects
        sphere = Sphere(radius=1, color=BLUE)
        sphere.set_opacity(0.6)

        cube = Cube(side_length=1.5, color=RED)
        cube.shift(RIGHT * 3)
        cube.set_opacity(0.6)

        # Animate
        self.play(Create(axes))
        self.wait()
        self.play(Create(sphere), Create(cube))
        self.wait()

        # Rotate camera
        self.begin_ambient_camera_rotation(rate=0.3)
        self.wait(5)
        self.stop_ambient_camera_rotation()


class Surface3D(ThreeDScene):
    def construct(self):
        # Set camera
        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES)

        # Create axes
        axes = ThreeDAxes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            z_range=[-3, 3, 1]
        )

        # Create surface: z = x^2 + y^2
        surface = Surface(
            lambda u, v: axes.c2p(u, v, u**2 + v**2),
            u_range=[-2, 2],
            v_range=[-2, 2],
            resolution=(20, 20),
            fill_opacity=0.7
        )
        surface.set_fill_by_value(
            axes=axes,
            colors=[(RED, -3), (YELLOW, 0), (GREEN, 3)],
            axis=2
        )

        # Labels
        title = Text("z = x² + y²", font_size=36)
        title.to_corner(UL)
        self.add_fixed_in_frame_mobjects(title)

        # Animate
        self.play(Create(axes))
        self.play(Write(title))
        self.play(Create(surface))
        self.wait()

        # Rotate
        self.begin_ambient_camera_rotation(rate=0.2)
        self.wait(8)
        self.stop_ambient_camera_rotation()


class ParametricCurve3D(ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES)

        axes = ThreeDAxes()

        # Parametric curve (helix)
        curve = ParametricFunction(
            lambda t: axes.c2p(
                np.cos(t),
                np.sin(t),
                t / 3
            ),
            t_range=[0, 3 * TAU],
            color=BLUE
        )

        self.play(Create(axes))
        self.play(Create(curve), run_time=3)
        self.wait()

        self.begin_ambient_camera_rotation(rate=0.3)
        self.wait(5)
