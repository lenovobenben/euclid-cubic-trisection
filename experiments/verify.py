"""Run exact replay and independent angle certificates with SageMath 10.7.

sage -python experiments/verify.py [--write]
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from sage.all import AA, QQ, PolynomialRing
from sage.env import SAGE_VERSION

from fixtures import fixtures, invalid_fixtures
from geometry import (Circle, CubicCurve, Line, circle_intersections, cross, dot,
                      line_circle_intersections, line_intersection, point,
                      squared_distance, subtract)
from records import exact_record, point_record
from trisection import construct_trisectors


ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ArithmeticError(message)


def unit_direction(start, end):
    direction = subtract(end, start)
    length = dot(direction, direction).sqrt()
    return tuple(value / length for value in direction)


def symbolic_checks():
    ring = PolynomialRing(QQ, "x,s,c,u,v")
    x, s, c, u, v = ring.gens()
    checks = []

    def check(expression, expected, label):
        require(expression == expected, label)
        checks.append(label)

    check(x ** 3 - (3 * x + c) / 4, (4 * x ** 3 - 3 * x - c) / 4,
          "line and given cubic encode the triple-angle equation")
    real_part = x ** 3 - 3 * x * s ** 2
    imaginary_part = 3 * x ** 2 * s - s ** 3
    check(real_part - (4 * x ** 3 - 3 * x), -3 * x * (x ** 2 + s ** 2 - 1),
          "triple rotation has the required real part on the unit circle")
    check(imaginary_part - s * (4 * x ** 2 - 1), -s * (x ** 2 + s ** 2 - 1),
          "triple rotation has the required imaginary part on the unit circle")
    check((2 * x ** 2 - 1) ** 2 + (2 * x * s) ** 2 - 1,
          4 * x ** 2 * (x ** 2 + s ** 2 - 1), "double-angle point lies on the unit circle")
    check((x - 1) ** 2 + s ** 2 - (2 - 2 * x), x ** 2 + s ** 2 - 1,
          "small chord encodes the cosine of the copied angle")
    check((2 * x ** 2 - 1 - x) ** 2 + (2 * x * s - s) ** 2 - (2 - 2 * x),
          (2 * x - 1) ** 2 * (x ** 2 + s ** 2 - 1),
          "second copied chord has the same length")
    check((u * x - v * s) ** 2 + (v * x + u * s) ** 2,
          (u ** 2 + v ** 2) * (x ** 2 + s ** 2), "angle transfer preserves length")
    check(u * (u * x - v * s) + v * (v * x + u * s),
          (u ** 2 + v ** 2) * x, "angle transfer preserves cosine")
    check(u * (v * x + u * s) - v * (u * x - v * s),
          (u ** 2 + v ** 2) * s, "angle transfer preserves orientation")
    return checks


def audit_trace(g):
    """Check each recorded geometric object against its own defining inputs."""
    known = {"O", "X", "Y", "V", "A", "B", "x_axis", "y_axis", "given_cubic"}
    for step in g.steps:
        inputs, outputs = step["inputs"], step["outputs"]
        operation = step["operation"]
        require(all(name in known for name in inputs), "trace uses an object before construction")
        require(all(name not in known for name in outputs), "trace overwrites an object")
        if operation == "line":
            line = g.lines[outputs[0]]
            require(all(line.value(g.points[name]) == 0 for name in inputs), "line incidence")
        elif operation in ("parallel", "perpendicular"):
            line, reference = g.lines[outputs[0]], g.lines[inputs[1]]
            require(line.value(g.points[inputs[0]]) == 0, "macro passes through its input point")
            if operation == "parallel":
                require(line.a * reference.b == line.b * reference.a, "parallel direction")
            else:
                require(line.a * reference.a + line.b * reference.b == 0, "perpendicular direction")
        elif operation == "midpoint":
            midpoint, first, second = g.points[outputs[0]], g.points[inputs[0]], g.points[inputs[1]]
            require(all(2 * midpoint[i] == first[i] + second[i] for i in range(2)), "midpoint")
        elif operation == "circle_with_transferred_radius":
            circle = g.circles[outputs[0]]
            require(circle.center == g.points[inputs[0]], "circle center")
            require(circle.radius_squared == squared_distance(g.points[inputs[1]], g.points[inputs[2]]),
                    "circle radius transfer")
        elif operation == "select":
            require(g.points[outputs[0]] in [g.points[name] for name in inputs], "selection membership")
        else:
            for name in outputs:
                at = g.points[name]
                for parent in inputs:
                    if parent == "given_cubic":
                        require(at[1] == at[0] ** 3, "cubic incidence")
                    elif parent in g.lines:
                        require(g.lines[parent].value(at) == 0, "intersection line incidence")
                    else:
                        require(g.circles[parent].value(at) == 0, "intersection circle incidence")
        known.update(outputs)


def verify_fixture(fixture):
    result = construct_trisectors(fixture["vertex"], fixture["first"], fixture["second"])
    g = result.construction
    audit_trace(g)
    first = unit_direction(fixture["vertex"], fixture["first"])
    last = unit_direction(fixture["vertex"], fixture["second"])
    cosine = dot(first, last)
    require(cosine == fixture["cosine"], "fixture angle and normalized rays disagree")
    require(g.points["C"][0] == cosine, "input angle copy and cosine projection")
    require(g.points["E"] == (0, cosine / 4), "constructed intercept")
    require(g.points["W"] == (1, AA(3) / 4), "positive reference slope")
    require(result.cubic_query_count == 1, "exactly one given-cubic query")
    cubic_step = next(step for step in g.steps if step["operation"] == "line_cubic_intersection")
    roots = [g.points[name][0] for name in cubic_step["outputs"]]
    require(len(roots) == 3 and len(set(roots)) == 3, "three distinct real cubic intersections")
    require(-1 < roots[0] < -AA(1) / 2 < roots[1] < 0 < AA(3).sqrt() / 2 < roots[2] < 1,
            "all three roots lie in their proved intervals")
    x = g.points["K"][0]
    require(x == roots[2] and 4 * x ** 3 - 3 * x == cosine, "correct positive root")
    require(g.points["F"] == (x, 0) and g.points["Q"][0] == x and g.points["Q"][1] > 0,
            "root projection and upper unit-circle lift")
    directions = [first, result.rays[0].direction, result.rays[1].direction, last]
    s = g.points["Q"][1]
    for direction in directions:
        require(dot(direction, direction) == 1, "normalized output ray")
    for left, right in zip(directions, directions[1:]):
        require(dot(left, right) == x, "each of the three adjacent angles has the same cosine")
        require(result.orientation * cross(left, right) == s and s > 0,
                "each adjacent angle has the same positive oriented sine")
    for ray in result.rays:
        require(ray.vertex == fixture["vertex"], "ray starts at original vertex")
        require(result.orientation * cross(first, ray.direction) > 0
                and result.orientation * cross(ray.direction, last) > 0, "ray strictly inside input angle")
    expected_x = {"rational_output_7_8": AA(7) / 8,
                  "quadratic_output_sqrt15_4": AA(15).sqrt() / 4}
    family = fixture["name"].split("/")[0]
    if family in expected_x:
        require(x == expected_x[family], "independent prescribed target root")
    return result, {"name": fixture["name"], "valid": True,
                    "input_cosine": exact_record(cosine), "target_cosine": exact_record(x),
                    "orientation": result.orientation, "cubic_intersection_count": len(roots)}


def primitive_checks():
    """Regression checks for tangent, vertical and empty intersection branches."""
    unit = Circle(point((0, 0)), AA(1))
    require(line_circle_intersections(Line(AA(1), AA(0), AA(-1)), unit) == [point((1, 0))],
            "tangent line-circle intersection")
    require(line_circle_intersections(Line(AA(1), AA(0), AA(-2)), unit) == [],
            "disjoint line-circle intersection")
    require(len(circle_intersections(unit, Circle(point((2, 0)), AA(1)))) == 1,
            "externally tangent circles")
    require(circle_intersections(unit, Circle(point((3, 0)), AA(1))) == [], "disjoint circles")
    curve = CubicCurve()
    require(curve.intersect(Line(AA(1), AA(0), AA(-2))) == [point((2, 8))], "vertical cubic query")
    require(curve.intersect(Line(AA(0), AA(1), AA(0))) == [point((0, 0))],
            "multiple cubic root is returned once")
    for action in (
        lambda: Line.through(point((0, 0)), point((0, 0))),
        lambda: line_intersection(Line(1, 0, 0), Line(1, 0, -1)),
        lambda: circle_intersections(unit, unit),
    ):
        try:
            action()
        except ValueError:
            continue
        raise ArithmeticError("degenerate primitive was accepted")
    return 9


def cli_checks():
    command = [sys.executable, str(ROOT / "experiments/trisection.py")]
    valid = subprocess.run(command + ["--vertex", "1/3", "-2/5", "--first", "4/3", "-2/5",
                                     "--second", "4/3", "3/5"], capture_output=True, text=True,
                           check=True)
    output = json.loads(valid.stdout)
    require(output["cubic_query_count"] == 1 and len(output["rays"]) == 2, "CLI output contract")
    require(all(ray["vertex"] == ["1/3", "-2/5"] for ray in output["rays"]),
            "CLI accepts and preserves negative fractional coordinates")
    for arguments in (["--first", "1", "0", "--second", "0", "1"],
                      ["--first", "invalid", "0", "--second", "1", "1"]):
        invalid = subprocess.run(command + arguments, capture_output=True, text=True)
        require(invalid.returncode == 2 and "Traceback" not in invalid.stderr,
                "CLI rejects invalid geometry or coordinates with a usage error")
    return 3


def example_record(result):
    g = result.construction
    return {
        "description": "60-degree input, translated and rotated, counterclockwise",
        "coordinate_system": "given orthonormal axes, common unit length 1",
        "points": {name: point_record(at) for name, at in g.points.items()},
        "lines": {name: [exact_record(value) for value in (line.a, line.b, line.c)]
                  for name, line in g.lines.items()},
        "circles": {name: {"center": point_record(circle.center),
                           "radius_squared": exact_record(circle.radius_squared)}
                    for name, circle in g.circles.items()},
        "steps": g.steps,
        "output_rays": [{"vertex": "V", "through": name} for name in ("R1", "R2")],
        "operation_counts": dict(sorted(Counter(step["operation"] for step in g.steps).items())),
        "cubic_query_count": result.cubic_query_count,
    }


def encoded_json(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="save exact report and example replay")
    args = parser.parse_args()
    identities = symbolic_checks()
    primitive_count = primitive_checks()
    cli_count = cli_checks()
    cases = []
    example = None
    for fixture in fixtures():
        result, certificate = verify_fixture(fixture)
        cases.append(certificate)
        if fixture["name"] == "60_degrees/translated_rotated_ccw":
            example = example_record(result)
    rejected = []
    for name, vertex, first, second in invalid_fixtures():
        try:
            construct_trisectors(vertex, first, second)
        except ValueError:
            rejected.append(name)
            continue
        raise ArithmeticError(f"invalid fixture was accepted: {name}")
    require(example is not None, "example fixture missing")
    example_bytes = encoded_json(example)
    source_paths = sorted((ROOT / "experiments").glob("*.py"))
    source_hashes = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in source_paths}
    report = {
        "valid": True,
        "sage_version": SAGE_VERSION,
        "symbolic_identity_count": len(identities),
        "symbolic_identities": identities,
        "primitive_check_count": primitive_count,
        "cli_check_count": cli_count,
        "fixture_count": len(cases),
        "invalid_input_count": len(rejected),
        "rejected_inputs": rejected,
        "cubic_queries_per_construction": 1,
        "cases": cases,
        "example_sha256": hashlib.sha256(example_bytes).hexdigest(),
        "source_sha256": source_hashes,
    }
    if args.write:
        atomic_write(ROOT / "experiments/results/example.json", example_bytes)
        atomic_write(ROOT / "experiments/results/verification.json", encoded_json(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
