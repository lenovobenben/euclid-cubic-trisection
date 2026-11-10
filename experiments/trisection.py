"""Construct both trisectors of an acute angle, using one given-cubic query.

Inputs V, A, B specify the rays VA and VB in the fixed orthonormal frame.
Only the intersection provider solves a cubic. All remaining operations
are the Euclidean primitives and classical macros in geometry.py.
"""

from dataclasses import dataclass

from geometry import Construction, CubicCurve, Line, cross, dot, point, subtract


@dataclass(frozen=True)
class Ray:
    vertex: tuple
    through: tuple

    @property
    def direction(self):
        return subtract(self.through, self.vertex)


@dataclass
class Trisection:
    construction: Construction
    rays: tuple
    orientation: int
    cubic_query_count: int


def construct_trisectors(vertex, first_ray_point, second_ray_point):
    """Accept any algebraic acute angle, in either orientation and at any position."""
    vertex, first_ray_point, second_ray_point = map(
        point, (vertex, first_ray_point, second_ray_point))
    first = subtract(first_ray_point, vertex)
    second = subtract(second_ray_point, vertex)
    determinant = cross(first, second)
    if determinant == 0 or dot(first, second) <= 0:
        raise ValueError("the input rays must bound a strictly acute angle")
    orientation = 1 if determinant > 0 else -1
    construction = Construction()
    for name, coordinates in (("O", (0, 0)), ("X", (1, 0)), ("Y", (0, 1)),
                              ("V", vertex), ("A", first_ray_point), ("B", second_ray_point)):
        construction.given_point(name, coordinates)
    g = construction
    # The two axes are given. Their definition is kept outside the action trace.
    g.lines["x_axis"] = Line.through(g.points["O"], g.points["X"])
    g.lines["y_axis"] = Line.through(g.points["O"], g.points["Y"])

    g.circle("unit_O", "O", "O", "X")
    g.circle("unit_V", "V", "O", "X")
    g.line("side_A", "V", "A")
    g.line("side_B", "V", "B")
    candidates = g.meet_line_circle("m", "side_A", "unit_V")
    g.select("M", candidates, lambda p: dot(subtract(p, vertex), first) > 0)
    candidates = g.meet_line_circle("n", "side_B", "unit_V")
    g.select("N", candidates, lambda p: dot(subtract(p, vertex), second) > 0)
    g.circle("input_chord", "X", "M", "N")
    candidates = g.meet_circles("p", "unit_O", "input_chord")
    g.select("P", candidates, lambda p: p[1] > 0)
    g.perpendicular("project_P", "P", "x_axis")
    g.meet_lines("C", "project_P", "x_axis")
    g.circle("transfer_cosine", "O", "O", "C")
    candidates = g.meet_line_circle("d", "y_axis", "transfer_cosine")
    g.select("D", candidates, lambda p: p[1] > 0)
    g.midpoint("D_half", "O", "D")
    g.midpoint("E", "O", "D_half")
    g.midpoint("Y_half", "O", "Y")
    g.midpoint("H", "Y_half", "Y")
    g.perpendicular("vertical_X", "X", "x_axis")
    g.parallel("horizontal_H", "H", "x_axis")
    g.meet_lines("W", "vertical_X", "horizontal_H")
    g.line("reference", "O", "W")
    g.parallel("L", "E", "reference")

    curve = CubicCurve()
    candidates = g.meet_cubic("k", "L", curve)
    g.select("K", candidates, lambda p: p[0] > 0)
    g.perpendicular("project_K", "K", "x_axis")
    g.meet_lines("F", "project_K", "x_axis")
    candidates = g.meet_line_circle("q", "project_K", "unit_O")
    g.select("Q", candidates, lambda p: p[1] > 0)

    def interior(at):
        direction = subtract(at, vertex)
        return (orientation * cross(first, direction) > 0
                and orientation * cross(direction, second) > 0)

    g.circle("first_small_chord", "M", "X", "Q")
    candidates = g.meet_circles("r_candidate_", "unit_V", "first_small_chord")
    g.select("R1", candidates, interior)
    g.circle("second_small_chord", "R1", "M", "R1")
    candidates = g.meet_circles("s_candidate_", "unit_V", "second_small_chord")
    g.select("R2", candidates, lambda p: p != g.points["M"])
    g.line("trisector_1", "V", "R1")
    g.line("trisector_2", "V", "R2")
    rays = (Ray(vertex, g.points["R1"]), Ray(vertex, g.points["R2"]))
    return Trisection(g, rays, orientation, curve.query_count)


def main():
    import argparse
    import json

    from sage.all import QQ

    from records import exact_record, point_record

    class RationalCoordinateParser(argparse.ArgumentParser):
        def _parse_optional(self, argument):
            # argparse recognizes negative decimals, but needs this extension for fractions.
            if argument.startswith("-") and "/" in argument:
                try:
                    QQ(argument)
                except (ValueError, TypeError, ZeroDivisionError):
                    return super()._parse_optional(argument)
                return None
            return super()._parse_optional(argument)

    parser = RationalCoordinateParser(description="Construct both trisectors from rational input points.")
    parser.add_argument("--vertex", nargs=2, type=QQ, default=(QQ(0), QQ(0)), metavar=("X", "Y"))
    parser.add_argument("--first", nargs=2, type=QQ, required=True, metavar=("X", "Y"))
    parser.add_argument("--second", nargs=2, type=QQ, required=True, metavar=("X", "Y"))
    args = parser.parse_args()
    try:
        result = construct_trisectors(args.vertex, args.first, args.second)
    except ValueError as error:
        parser.error(str(error))
    g = result.construction
    print(json.dumps({
        "input_cosine": exact_record(g.points["C"][0]),
        "trisected_angle_cosine": exact_record(g.points["K"][0]),
        "rays": [{"vertex": point_record(ray.vertex), "through": point_record(ray.through)}
                 for ray in result.rays],
        "orientation": result.orientation,
        "cubic_query_count": result.cubic_query_count,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
