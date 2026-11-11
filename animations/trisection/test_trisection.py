"""Check the actual movie sequence, its dependencies and close-point geometry."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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

    def test_distinct_view_scales(self):
        scene = self.scene
        left_circle = scene.objects["unit_V"]
        right_circle = scene.objects["unit_O"]
        self.assertAlmostEqual(left_circle.width / right_circle.width, 1.3)
        self.assertAlmostEqual(scene.original_view.scale / scene.coordinate_view.scale, 1.3)
        self.assertEqual(scene.left_scale_label.text.replace(" ", ""), "左视图×1.3")
        self.assertEqual(scene.right_scale_label.text.replace(" ", ""), "右视图×1")
        for name in ("M", "N", "R1", "R2"):
            self.assertAlmostEqual(np.linalg.norm(scene.dots[name].get_center() - left_circle.get_center()),
                                   left_circle.width / 2)
        self.assertGreaterEqual(left_circle.get_left()[0], -6.35)
        self.assertLessEqual(left_circle.get_right()[0], -1.6)
        self.assertGreaterEqual(left_circle.get_bottom()[1], -3.0)
        self.assertLessEqual(left_circle.get_top()[1], 2.25)
        self.assertGreater(scene.left_scale_label.get_bottom()[1], -3.25)

    def test_timeline_follows_each_movie_output(self):
        scene = self.scene
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            outputs = [(3840, 2160, 60, "CubicTrisection.mp4"),
                       (1280, 720, 30, "CubicTrisection.mp4"),
                       (1280, 720, 30, "custom-preview.mp4")]
            manifests = []
            for width, height, fps, filename in outputs:
                movie = directory / f"{height}p{fps}" / filename
                with tempconfig({"pixel_width": width, "pixel_height": height, "frame_rate": fps}):
                    with patch.object(scene.renderer.file_writer, "movie_file_path", str(movie), create=True):
                        scene.write_timeline()
                manifests.append(movie.with_suffix(".timeline.json"))
            self.assertEqual(len(set(manifests)), 3)
            for manifest, (width, height, fps, filename) in zip(manifests, outputs):
                data = json.loads(manifest.read_text("utf-8"))
                self.assertEqual(data["resolution"], [width, height])
                self.assertEqual(data["frame_rate"], fps)
                self.assertEqual(data["movie_file"], filename)
                self.assertEqual(data["geometry_sha256"], scene.geometry_hash)
            self.assertFalse((directory / "timeline.json").exists())


if __name__ == "__main__":
    unittest.main()
