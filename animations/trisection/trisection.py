"""A complete original-position trisection using verified geometric data."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
from manim import (
    Arc, Circle, Create, Dot, FadeIn, FadeOut, Indicate, Line, Rectangle,
    Scene, Text, VGroup, VMobject, config,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FONT = "Noto Sans CJK SC"
BACKGROUND = "#07101F"
FOREGROUND = "#E8F0F7"
MUTED = "#8397A8"
INPUT = "#F45BFF"
CURRENT = "#FFC857"
AUXILIARY = "#8AC6D9"
RESULT = "#5DE2A5"


def load_geometry():
    payload = (HERE / "geometry.json").read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != (HERE / "geometry.sha256").read_text("ascii").strip():
        raise ArithmeticError("animation geometry does not match its saved digest")
    data = json.loads(payload)
    report = json.loads((ROOT / "experiments/results/verification.json").read_text("utf-8"))
    example = (ROOT / "experiments/results/example.json").read_bytes()
    if (not report["valid"] or data["source_example_sha256"] != report["example_sha256"]
            or hashlib.sha256(example).hexdigest() != report["example_sha256"]
            or data["source_sha256"] != report["source_sha256"]):
        raise ArithmeticError("animation data does not match the exact verification report")
    for name, expected in data["source_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ArithmeticError(f"source changed since verification: {name}")
    if data["cubic_query_count"] != 1:
        raise ArithmeticError("the construction must use exactly one cubic query")
    return data, digest


@dataclass(frozen=True)
class View:
    origin: tuple
    offset: tuple
    scale: float

    def at(self, point):
        position = (np.array(point) - np.array(self.origin)) * self.scale + np.array(self.offset)
        return np.array([*position, 0.0])

    def line(self, coefficients, bounds, color=CURRENT, width=1.5):
        a, b, c = coefficients
        left, right, bottom, top = bounds
        candidates = []
        if abs(b) > 1e-14:
            for x in (left, right):
                y = -(a * x + c) / b
                if bottom <= y <= top:
                    candidates.append([x, y])
        if abs(a) > 1e-14:
            for y in (bottom, top):
                x = -(b * y + c) / a
                if left <= x <= right:
                    candidates.append([x, y])
        if len(candidates) < 2:
            raise ArithmeticError("the display line misses its viewport")
        first, second = max(((p, q) for p in candidates for q in candidates),
                            key=lambda pair: np.linalg.norm(np.array(pair[0]) - np.array(pair[1])))
        return Line(self.at(first), self.at(second), color=color, stroke_width=width)


class CubicTrisection(Scene):
    def text(self, content, size=25, color=FOREGROUND):
        return Text(content, font=FONT, font_size=size, color=color, line_spacing=1.15)

    def stage(self, title):
        self.sections.append({"title": title, "start_seconds": round(float(self.time), 6)})
        heading = self.text(title, 33).move_to([-6.35, 3.47, 0], aligned_edge=np.array([-1, 0, 0]))
        if hasattr(self, "heading"):
            self.play(FadeOut(self.heading), FadeIn(heading), run_time=0.4)
        else:
            self.play(FadeIn(heading), run_time=0.4)
        self.heading = heading

    def caption(self, content, hold=0.5):
        replacement = self.text(content, 25, CURRENT)
        if replacement.width > 12.5:
            replacement.scale_to_fit_width(12.5)
        replacement.move_to([0, -3.48, 0])
        if hasattr(self, "caption_object"):
            self.remove(self.caption_object)
        self.caption_object = replacement
        self.add(replacement)
        self.wait(hold)

    def dependencies(self, name):
        step = self.definitions.get(name)
        if step is None:
            return []
        if step["operation"] == "select":
            return list(dict.fromkeys(parent for candidate in step["inputs"]
                                      for parent in self.definitions[candidate]["inputs"]))
        return step["inputs"]

    def reveal(self, name):
        parents = self.dependencies(name)
        missing = [parent for parent in parents if parent not in self.available]
        if missing:
            raise ArithmeticError(f"{name} appeared before its parents: {missing}")
        self.available.add(name)
        self.audit.append({"object": name, "parents": parents,
                           "seconds": round(float(self.time), 6)})

    def draw(self, name, mobject, duration=0.7):
        self.reveal(name)
        self.objects[name] = mobject
        self.play(Create(mobject), run_time=duration)
        return mobject

    def mark(self, name, view=None, label=None, offset=(0.2, 0.2), color=AUXILIARY,
             leader=False, radius=0.035):
        self.reveal(name)
        view = self.coordinate_view if view is None else view
        at = view.at(self.data["points"][name])
        dot = Dot(at, radius=radius, color=color)
        group = VGroup(dot)
        if label != "":
            label_object = self.text(name if label is None else label, 22, color)
            label_object.move_to(at + np.array([*offset, 0]))
            if leader:
                direction = label_object.get_center() - at
                end = label_object.get_boundary_point(-direction)
                group.add(Line(at, end, color=color, stroke_width=0.8, buff=0.04))
            group.add(label_object)
            self.labels[name] = label_object
        self.objects[name] = group
        self.dots[name] = dot
        self.play(FadeIn(group), run_time=0.4)
        return group

    def draw_circle(self, name, view=None, opacity=0.75):
        view = self.coordinate_view if view is None else view
        circle = self.data["circles"][name]
        return self.draw(name, Circle(radius=circle["radius"] * view.scale,
                                      color=CURRENT, stroke_width=1.4, stroke_opacity=opacity)
                         .move_to(view.at(circle["center"])))

    def draw_line(self, name, color=CURRENT):
        return self.draw(name, self.coordinate_view.line(self.data["lines"][name], self.bounds, color))

    def chord(self, first, second, view, color=CURRENT):
        return Line(view.at(self.data["points"][first]), view.at(self.data["points"][second]),
                    color=color, stroke_width=2)

    def dim(self, names, opacity=0.16):
        objects = [self.objects[name] for name in names if name in self.objects]
        if objects:
            animations = []
            for item in objects:
                if isinstance(item, VGroup):
                    animations.append(item.animate.set_opacity(opacity))
                else:
                    animations.append(item.animate.set_stroke(opacity=opacity))
            self.play(*animations, run_time=0.4)

    def construct(self):
        config.background_color = BACKGROUND
        self.data, self.geometry_hash = load_geometry()
        self.objects, self.labels, self.dots = {}, {}, {}
        self.audit, self.sections = [], []
        self.available = {"O", "X", "Y", "V", "A", "B", "x_axis", "y_axis", "given_cubic"}
        self.definitions = {name: step for step in self.data["steps"] for name in step["outputs"]}
        self.coordinate_view = View((0, 0), (2.8, -0.65), 1.65)
        self.original_magnification = 1.3
        self.original_view = View(tuple(self.data["points"]["V"]), (-4.0, -0.7),
                                  self.coordinate_view.scale * self.original_magnification)
        self.bounds = (-1.25, 1.65, -1.35, 1.65)
        self.principle_page()
        self.input_and_copy()
        self.cosine_and_intercept()
        self.reference_and_line()
        self.intersect_and_select()
        self.lift_to_circle()
        self.restore_rays()
        if not config.dry_run and config.write_to_movie:
            self.write_timeline()

    def write_timeline(self):
        movie = Path(self.renderer.file_writer.movie_file_path)
        manifest = {
            "scene": type(self).__name__,
            "movie_file": movie.name,
            "geometry_sha256": self.geometry_hash,
            "animation_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "resolution": [config.pixel_width, config.pixel_height],
            "frame_rate": config.frame_rate,
            "duration_seconds": round(float(self.time), 6),
            "display_scales": {"original": self.original_view.scale,
                               "coordinate": self.coordinate_view.scale,
                               "original_relative_to_coordinate": self.original_magnification},
            "sections": self.sections,
            "construction_events": self.audit,
        }
        destination = movie.with_suffix(".timeline.json")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", "utf-8")

    def principle_page(self):
        self.sections.append({"title": "原理", "start_seconds": 0})
        title = self.text("借助立方曲线三等分角", 43).move_to([0, 2.45, 0])
        lines = VGroup(
            self.text("余弦三倍角公式   4t³ − 3t = cos θ", 29).move_to([0, 1.2, 0]),
            self.text("作直线 y = ¾x + ¼cos θ，与给定 y = x³ 求交", 27, AUXILIARY)
                .move_to([0, 0.25, 0]),
            self.text("取第一象限交点，回到单位圆得到 θ/3", 27, RESULT).move_to([0, -0.7, 0]),
            self.text("在原角复制两次相同弦长，作出两条三等分射线", 26).move_to([0, -1.65, 0]),
        )
        self.play(FadeIn(title), run_time=0.7)
        self.play(FadeIn(lines), run_time=0.8)
        self.wait(5)
        self.play(FadeOut(title), FadeOut(lines), run_time=0.5)

    def input_and_copy(self):
        self.stage("把给定角复制到坐标原点")
        rule = Line([-6.35, 3.03, 0], [6.35, 3.03, 0], color=MUTED, stroke_width=0.6)
        self.add(rule)
        self.left_heading = self.text("给定锐角 ∠AVB", 23).move_to([-4, 2.55, 0])
        self.add(self.left_heading, self.text("给定坐标系与 y = x³", 23).move_to([2.9, 2.55, 0]))
        self.left_scale_label = self.text(f"左视图 ×{self.original_magnification:g}", 17, MUTED)
        self.left_scale_label.move_to([-4, -3.04, 0])
        self.right_scale_label = self.text("右视图 ×1", 17, MUTED).move_to([2.9, -3.04, 0])
        self.add(self.left_scale_label, self.right_scale_label)
        self.caption("原角可位于任意位置，坐标系、单位长度和立方曲线已给定", hold=1.2)
        for name in ("x_axis", "y_axis"):
            self.objects[name] = self.coordinate_view.line(self.data["lines"][name], self.bounds,
                                                          MUTED, width=0.8)
        self.play(*[Create(self.objects[name]) for name in ("x_axis", "y_axis")], run_time=0.7)
        for name, offset in (("O", (0.2, -0.22)), ("X", (0.23, -0.17)), ("Y", (-0.2, 0.15))):
            self.mark(name, offset=offset)
        curve = VMobject(color=INPUT, stroke_width=2, stroke_opacity=0.55)
        curve.set_points_as_corners([self.coordinate_view.at(at) for at in self.data["cubic_samples"]])
        self.objects["given_cubic"] = curve
        self.play(Create(curve), run_time=0.9)
        self.curve_label = self.text("y = x³", 22, INPUT).move_to([4.45, 2.1, 0])
        self.add(self.curve_label)
        self.mark("V", self.original_view, offset=(-0.2, -0.23))
        vertex = np.array(self.data["points"]["V"])
        for name, endpoint, offset in (("side_A", "M", (0.28, 0.05)),
                                       ("side_B", "N", (-0.25, 0.13))):
            direction = np.array(self.data["points"][endpoint]) - vertex
            end = vertex + 1.35 * direction
            ray = Line(self.original_view.at(vertex), self.original_view.at(end),
                       color=INPUT, stroke_width=1.9)
            self.draw(name, ray)
            label = self.text("VA" if name == "side_A" else "VB", 22, INPUT)
            label.move_to(self.original_view.at(end) + np.array([*offset, 0]))
            self.objects[f"{name}_label"] = label
            self.add(label)
        self.caption("以 O、V 为圆心，分别作单位圆", hold=1.2)
        self.draw_circle("unit_O").set_color(AUXILIARY)
        self.draw_circle("unit_V", self.original_view).set_color(AUXILIARY)
        self.caption("取原角两条射线与单位圆的交点 M、N", hold=1)
        self.mark("M", self.original_view, offset=(0.28, -0.18), color=INPUT)
        self.mark("N", self.original_view, offset=(-0.23, 0.18), color=INPUT)
        self.chord_MN = self.chord("M", "N", self.original_view)
        self.play(Create(self.chord_MN), run_time=0.6)
        self.caption("以 X 为圆心、MN 为半径作圆", hold=1.3)
        self.draw_circle("input_chord")
        self.caption("取上半平面交点 P，得到与原角相等的 ∠XOP", hold=1.2)
        self.mark("P", offset=(0.2, 0.22), color=INPUT)
        self.OP = self.chord("O", "P", self.coordinate_view, INPUT)
        self.play(Create(self.OP), run_time=0.7)
        self.wait(1.6)
        self.dim(["input_chord"], 0)
        self.chord_MN.set_opacity(0.25)
        self.left_objects = [self.objects[name] for name in
                             ("V", "side_A", "side_B", "side_A_label", "side_B_label", "unit_V", "M", "N")]
        self.left_objects.append(self.chord_MN)
        self.left_objects.append(self.left_scale_label)

    def cosine_and_intercept(self):
        self.stage("取得余弦，并两次中分构造截距")
        self.caption("过 P 作 x 轴的垂线，与轴交于 C", hold=1.2)
        self.draw_line("project_P")
        self.mark("C", offset=(0.22, -0.25))
        self.caption("以 O 为圆心、OC 为半径作圆，取正 y 轴交点 D", hold=1.4)
        self.draw_circle("transfer_cosine")
        self.mark("D", offset=(-0.23, 0.23))
        self.caption("放大 OD，连续两次取中点，得到 E = (0, c/4)", hold=1.2)
        self.play(*[FadeOut(item) for item in self.left_objects], FadeOut(self.left_heading), run_time=0.4)
        self.intercept_view = View((0, 0), (-4, -1.8), 6.4)
        detail = self.intercept_detail()
        self.play(FadeIn(detail), run_time=0.4)
        self.caption("先作 OD 的中点 D½", hold=0.8)
        self.mark("D_half", label="", radius=0.028)
        half = self.detail_marker("D_half", self.intercept_view, "D½", (0.4, 0), AUXILIARY)
        self.play(FadeIn(half), run_time=0.5)
        self.wait(0.8)
        self.caption("再作 OD½ 的中点 E，截距 OE = c/4", hold=1)
        self.mark("E", offset=(-0.82, 0.12), leader=True, color=CURRENT, radius=0.028)
        quarter = self.detail_marker("E", self.intercept_view, "E  (0, c/4)", (1.0, 0), CURRENT)
        self.play(FadeIn(quarter), run_time=0.5)
        self.wait(1.7)
        self.play(FadeOut(detail), FadeOut(half), FadeOut(quarter), run_time=0.4)
        self.play(*[FadeIn(item) for item in self.left_objects], FadeIn(self.left_heading), run_time=0.4)
        self.dim(["project_P", "transfer_cosine", "D_half"], 0.1)

    def detail_marker(self, name, view, label, offset, color):
        at = view.at(self.data["points"][name])
        dot = Dot(at, radius=0.035, color=color)
        text = self.text(label, 23, color).move_to(at + np.array([*offset, 0]))
        return VGroup(dot, text)

    def intercept_detail(self):
        view = self.intercept_view
        frame = Rectangle(width=4.5, height=4.75, stroke_width=0.8, color=MUTED)
        frame.move_to([-4, -0.15, 0])
        heading = self.text("OD 的局部放大", 23).move_to([-4, 2.0, 0])
        axis = Line(view.at((0, -0.04)), view.at((0, 0.54)), color=AUXILIARY, stroke_width=1.1)
        return VGroup(frame, heading, axis,
                      self.detail_marker("O", view, "O", (-0.3, -0.12), AUXILIARY),
                      self.detail_marker("D", view, "D  (0, c)", (-0.9, 0), AUXILIARY))

    def reference_and_line(self):
        self.stage("构造正斜率方向，过 E 作直线 L")
        self.caption("作 OY 中点 Y½，本例中它与已有点 D 重合", hold=1.6)
        self.reveal("Y_half")
        self.objects["Y_half"] = self.objects["D"]
        old_label = self.labels["D"]
        new_label = self.text("D = Y½", 20, AUXILIARY).move_to(
            self.coordinate_view.at(self.data["points"]["D"]) + np.array([-0.65, -0.1, 0]))
        self.play(FadeOut(old_label), FadeIn(new_label), run_time=0.4)
        self.objects["D"].remove(old_label)
        self.objects["D"].add(new_label)
        self.labels["D"] = new_label
        self.caption("作 Y½Y 的中点 H，得到 H = (0, 3/4)", hold=1.2)
        self.mark("H", offset=(-0.23, -0.18))
        self.caption("过 X 作竖直线，过 H 作水平线，交于 W", hold=1.3)
        self.draw_line("vertical_X")
        self.draw_line("horizontal_H")
        self.mark("W", offset=(0.3, -0.27))
        self.caption("连接 OW，得到斜率为正 3/4 的参考线", hold=1.3)
        self.draw_line("reference", AUXILIARY)
        self.caption("过 E 作 OW 的平行线 L", hold=1.2)
        self.draw_line("L")
        self.line_label = self.text("L ∥ OW", 24, CURRENT).move_to([5.05, 1.55, 0])
        self.play(FadeIn(self.line_label), run_time=0.4)
        self.wait(1.5)

    def intersect_and_select(self):
        self.stage("与给定立方曲线求交，选第一象限交点")
        self.caption("L 与 y = x³ 相交，得到三个不同的实交点", hold=1.6)
        self.dim(["P", "C", "D", "D_half", "E", "H", "W", "project_P", "transfer_cosine"], 0)
        self.dim(["vertical_X", "horizontal_H", "reference"], 0.1)
        self.play(self.OP.animate.set_stroke(opacity=0), self.objects["given_cubic"].animate.set_stroke(opacity=1),
                  FadeOut(self.line_label), run_time=0.4)
        for name in ("k0", "k1", "k2"):
            self.mark(name, label="", color=AUXILIARY)
        self.wait(1.6)
        self.caption("取唯一的第一象限交点 K，它的横坐标为正", hold=1.5)
        self.mark("K", offset=(0.26, -0.14), color=RESULT)
        self.objects["k2"].set_opacity(0)
        self.play(Indicate(self.dots["K"], color=RESULT, scale_factor=1.8), run_time=0.7)
        self.wait(1.2)

    def root_detail(self):
        view = View((0.95, 0.22), (-4, -0.2), 7.0)
        frame = Rectangle(width=4.5, height=4.75, stroke_width=0.8, color=MUTED).move_to([-4, -0.15, 0])
        heading = self.text("单位圆取点的局部放大", 23).move_to([-4, 2.0, 0])
        axis = Line(view.at((0.78, 0)), view.at((1.13, 0)), color=MUTED, stroke_width=1)
        angles = np.linspace(0, 0.52, 160)
        arc = VMobject(color=AUXILIARY, stroke_width=1.5)
        arc.set_points_as_corners([view.at((np.cos(angle), np.sin(angle))) for angle in angles])
        t = self.data["points"]["F"][0]
        projection = Line(view.at((t, -0.025)), view.at((t, 0.5)), color=CURRENT, stroke_width=1.4)
        f = self.detail_marker("F", view, "F", (-0.12, -0.28), CURRENT)
        x = self.detail_marker("X", view, "X", (0.18, -0.28), AUXILIARY)
        q = self.detail_marker("Q", view, "Q", (0.25, 0.12), RESULT)
        return {"view": view, "frame": VGroup(frame, heading), "axis": axis, "arc": arc,
                "projection": projection, "F": f, "X": x, "Q": q}

    def lift_to_circle(self):
        self.stage("投影正根横坐标，回到单位圆取点 Q")
        self.caption("过 K 作 x 轴的垂线，取得投影点 F", hold=1.3)
        self.dim(["L", "given_cubic", "k0", "k1"], 0.12)
        self.dim(["vertical_X", "horizontal_H", "reference"], 0)
        self.draw_line("project_K")
        self.mark("F", offset=(-0.48, -0.48), color=CURRENT, leader=True, radius=0.028)
        self.caption("复用这条垂线，与单位圆求交，取上半平面的 Q", hold=1.4)
        self.mark("Q", offset=(0.26, 0.1), color=RESULT, radius=0.03)
        self.play(*[FadeOut(item) for item in self.left_objects], FadeOut(self.left_heading), run_time=0.4)
        detail = self.root_detail()
        group = VGroup(detail["frame"], detail["axis"], detail["arc"], detail["projection"],
                       detail["F"], detail["X"], detail["Q"])
        self.play(FadeIn(group), run_time=0.5)
        self.wait(2.2)
        self.play(FadeOut(group), run_time=0.4)
        self.play(*[FadeIn(item) for item in self.left_objects], FadeIn(self.left_heading), run_time=0.4)
        self.caption("连接 OQ，得到三分之一角 ∠XOQ = θ/3", hold=1.4)
        self.OQ = self.chord("O", "Q", self.coordinate_view, RESULT)
        self.play(Create(self.OQ), run_time=0.7)
        q = self.data["points"]["Q"]
        angle = np.arctan2(q[1], q[0])
        arc = Arc(radius=0.58, start_angle=0, angle=angle, color=RESULT, stroke_width=1.4)
        arc.shift(self.coordinate_view.at((0, 0)))
        label = self.text("θ/3", 20, RESULT).move_to([3.45, -0.15, 0])
        self.play(Create(arc), FadeIn(label), run_time=0.5)
        self.caption("连接 XQ，取得三分之一角对应的单位圆弦", hold=1.3)
        self.chord_XQ = self.chord("X", "Q", self.coordinate_view)
        self.play(Create(self.chord_XQ), run_time=0.6)
        self.wait(1.3)

    def draw_original_ray(self, name, endpoint):
        vertex = np.array(self.data["points"]["V"])
        direction = np.array(self.data["points"][endpoint]) - vertex
        ray = Line(self.original_view.at(vertex), self.original_view.at(vertex + 1.35 * direction),
                   color=RESULT, stroke_width=2.3)
        return self.draw(name, ray)

    def restore_rays(self):
        self.stage("把相同弦长转回原角，作出两条射线")
        self.caption("以 M 为圆心、XQ 为半径作圆，与原角单位圆相交", hold=1.6)
        self.draw_circle("first_small_chord", self.original_view)
        self.caption("取原角内部的交点 R₁", hold=1.2)
        self.mark("R1", self.original_view, "R₁", (0.33, 0.1), RESULT)
        chord_one = self.chord("M", "R1", self.original_view)
        self.play(Create(chord_one), run_time=0.5)
        self.caption("作射线 VR₁，得到第一条三等分射线", hold=1.4)
        self.draw_original_ray("trisector_1", "R1")
        self.caption("以 R₁ 为圆心、过 M 作圆，再与单位圆相交", hold=1.5)
        self.draw_circle("second_small_chord", self.original_view)
        self.play(Indicate(self.dots["M"], color=CURRENT), run_time=0.6)
        self.caption("已有交点为 M，取另一个交点 R₂", hold=1.5)
        self.mark("R2", self.original_view, "R₂", (-0.32, 0.2), RESULT)
        chord_two = self.chord("R1", "R2", self.original_view)
        self.play(Create(chord_two), run_time=0.5)
        self.caption("作射线 VR₂，得到第二条三等分射线", hold=1.4)
        self.draw_original_ray("trisector_2", "R2")
        self.dim(["first_small_chord", "second_small_chord"], 0)
        self.play(chord_one.animate.set_stroke(opacity=0), chord_two.animate.set_stroke(opacity=0),
                  self.chord_MN.animate.set_stroke(opacity=0), run_time=0.4)
        self.stage("原角的两条三等分射线已作成")
        vertex = np.array(self.data["points"]["V"])
        directions = [np.array(self.data["points"][name]) - vertex for name in ("M", "R1", "R2", "N")]
        self.final_labels = []
        for first, second in zip(directions, directions[1:]):
            start = np.arctan2(first[1], first[0])
            end = np.arctan2(second[1], second[0])
            arc = Arc(radius=0.72 * self.original_magnification, start_angle=start, angle=end - start,
                      color=RESULT, stroke_width=1.5).shift(self.original_view.at(vertex))
            middle = (start + end) / 2
            at = (self.original_view.at(vertex)
                  + np.array([np.cos(middle), np.sin(middle), 0]) * 1.28 * self.original_magnification)
            numerator = self.text("θ", 18, RESULT).move_to([0, 0.13, 0])
            denominator = self.text("3", 16, RESULT).move_to([0, -0.14, 0])
            bar = Line([-0.105, 0, 0], [0.105, 0, 0], color=RESULT, stroke_width=0.8)
            label = VGroup(numerator, bar, denominator).move_to(at)
            self.final_labels.append(label)
            self.play(Create(arc), FadeIn(label), run_time=0.4)
        self.caption("VR₁、VR₂ 从原顶点出发，把给定锐角分成三个相等的角", hold=1.6)
        self.wait(4)
