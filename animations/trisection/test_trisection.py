"""Check the actual movie sequence, its dependencies and close-point geometry."""

import tempfile
import unittest

import numpy as np
from manim import Text, tempconfig

from trisection import CubicTrisection, View, load_geometry


class AnimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.enterClassContext(tempconfig({
            "media_dir": directory.name, "dry_run": True, "skip_animations": True,
            "progress_bar": "none", "verbosity": "ERROR",
            "pixel_width": 1280, "pixel_height": 720,
        }))
        cls.scene = CubicTrisection()
        cls.scene.render()

    def test_complete_documented_sequence(self):
        names = [event["object"] for event in self.scene.audit]
        expected = ["unit_O", "unit_V", "M", "N", "input_chord", "P", "project_P", "C",
                    "transfer_cosine", "D", "D_half", "E", "Y_half", "H", "vertical_X",
                    "horizontal_H", "W", "reference", "L", "k0", "k1", "k2", "K",
                    "project_K", "F", "Q", "first_small_chord", "R1", "trisector_1",
                    "second_small_chord", "R2", "trisector_2"]
        positions = [names.index(name) for name in expected]
        self.assertEqual(positions, sorted(positions))
        known = {"O", "X", "Y", "V", "A", "B", "x_axis", "y_axis", "given_cubic"}
        for event in self.scene.audit:
            self.assertTrue(set(event["parents"]).issubset(known), event)
            known.add(event["object"])
        self.assertEqual(self.scene.data["cubic_query_count"], 1)
        self.assertEqual(len(self.scene.sections), 8)

    def test_main_and_detail_incidence(self):
        data, _ = load_geometry()
        for view in (self.scene.coordinate_view, View((0.95, 0.22), (-4, -0.2), 7)):
            for name, points in (("project_K", ("K", "F", "Q")),
                                  ("L", ("E", "K")), ("reference", ("O", "W"))):
                line = view.line(data["lines"][name], (-2, 2, -2, 2))
                start, end = line.get_start()[:2], line.get_end()[:2]
                direction = end - start
                for point in points:
                    at = view.at(data["points"][point])[:2]
                    residual = abs(np.linalg.det(np.array([direction, at - start])))
                    self.assertLess(residual / np.linalg.norm(direction), 1e-9)
            center = view.at((0, 0))
            for name in ("X", "Y", "P", "Q"):
                self.assertAlmostEqual(np.linalg.norm(view.at(data["points"][name]) - center), view.scale)

    def test_close_points_and_detail_labels(self):
        scene = self.scene
        f, x = scene.dots["F"], scene.dots["X"]
        self.assertGreater(np.linalg.norm(f.get_center() - x.get_center()), (f.width + x.width) / 2)
        self.assertLess(np.linalg.norm(scene.labels["F"].get_center() - f.get_center()),
                        np.linalg.norm(scene.labels["F"].get_center() - x.get_center()))
        detail = scene.root_detail()
        for name in ("F", "X", "Q"):
            dot, label = detail[name]
            for other in ("F", "X", "Q"):
                if name == other:
                    continue
                other_dot, other_label = detail[other]
                self.assertGreater(np.linalg.norm(dot.get_center() - other_dot.get_center()),
                                   (dot.width + other_dot.width) / 2)
                self.assertLess(np.linalg.norm(label.get_center() - dot.get_center()),
                                np.linalg.norm(label.get_center() - other_dot.get_center()))
                separation_x = abs(label.get_x() - other_label.get_x()) - (label.width + other_label.width) / 2
                separation_y = abs(label.get_y() - other_label.get_y()) - (label.height + other_label.height) / 2
                self.assertTrue(separation_x > 0 or separation_y > 0)

    def test_coincident_midpoint_reuse(self):
        scene = self.scene
        np.testing.assert_allclose(scene.data["points"]["D"], scene.data["points"]["Y_half"])
        self.assertIs(scene.objects["D"], scene.objects["Y_half"])
        self.assertEqual(scene.labels["D"].text.replace(" ", ""), "D=Y½")
        for name, others in (("D", ("H", "Y")), ("H", ("D", "Y"))):
            label = scene.labels[name]
            for other in others:
                self.assertLess(np.linalg.norm(label.get_center() - scene.dots[name].get_center()),
                                np.linalg.norm(label.get_center() - scene.dots[other].get_center()))

    def test_final_text_within_frame(self):
        seen = set()
        for root in self.scene.mobjects:
            for item in root.get_family():
                if not isinstance(item, Text) or id(item) in seen:
                    continue
                seen.add(id(item))
                self.assertGreaterEqual(item.get_left()[0], -7.11)
                self.assertLessEqual(item.get_right()[0], 7.11)
                self.assertGreaterEqual(item.get_bottom()[1], -3.95)
                self.assertLessEqual(item.get_top()[1], 3.95)

    def test_unfilled_curves_and_separated_final_angles(self):
        for name in ("given_cubic", "unit_O", "unit_V", "input_chord", "transfer_cosine",
                     "first_small_chord", "second_small_chord"):
            self.assertEqual(self.scene.objects[name].get_fill_opacity(), 0, name)
        labels = self.scene.final_labels
        self.assertEqual(len(labels), 3)
        for first, second in zip(labels, labels[1:]):
            horizontal_gap = abs(first.get_x() - second.get_x()) - (first.width + second.width) / 2
            vertical_gap = abs(first.get_y() - second.get_y()) - (first.height + second.height) / 2
            self.assertTrue(horizontal_gap > 0.03 or vertical_gap > 0.03)

    def test_point_labels_clear_their_supporting_lines(self):
        scene = self.scene
        checks = (("O", "x_axis", scene.coordinate_view), ("O", "y_axis", scene.coordinate_view),
                  ("C", "project_P", scene.coordinate_view), ("C", "x_axis", scene.coordinate_view),
                  ("H", "horizontal_H", scene.coordinate_view),
                  ("W", "horizontal_H", scene.coordinate_view), ("W", "vertical_X", scene.coordinate_view),
                  ("W", "reference", scene.coordinate_view), ("K", "L", scene.coordinate_view),
                  ("R1", "trisector_1", scene.original_view), ("R2", "trisector_2", scene.original_view))
        for point_name, line_name, view in checks:
            with self.subTest(point=point_name, line=line_name):
                line = view.line(scene.data["lines"][line_name], (-30, 30, -30, 30))
                direction = line.get_end()[:2] - line.get_start()[:2]
                normal = np.array([-direction[1], direction[0]]) / np.linalg.norm(direction)
                label = scene.labels[point_name]
                distance = abs(np.dot(normal, label.get_center()[:2] - line.get_start()[:2]))
                half_projection = abs(normal[0]) * label.width / 2 + abs(normal[1]) * label.height / 2
                self.assertGreater(distance - half_projection, 0.025)


if __name__ == "__main__":
    unittest.main()
