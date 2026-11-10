"""Exact Euclidean primitives and the classical macros in docs/CONSTRUCTION.md."""

from dataclasses import dataclass

from sage.all import AA, PolynomialRing


def point(coordinates):
    values = tuple(AA(value) for value in coordinates)
    if len(values) != 2:
        raise ValueError("a point needs exactly two coordinates")
    return values


def subtract(first, second):
    return (first[0] - second[0], first[1] - second[1])


def dot(first, second):
    return first[0] * second[0] + first[1] * second[1]


def cross(first, second):
    return first[0] * second[1] - first[1] * second[0]


def squared_distance(first, second):
    difference = subtract(first, second)
    return dot(difference, difference)


@dataclass(frozen=True)
class Line:
    a: object
    b: object
    c: object

    @classmethod
    def through(cls, first, second):
        if first == second:
            raise ValueError("a line needs two different points")
        dx, dy = subtract(second, first)
        return cls(-dy, dx, dy * first[0] - dx * first[1])

    def value(self, at):
        return self.a * at[0] + self.b * at[1] + self.c

    def parallel(self, at):
        return Line(self.a, self.b, -self.a * at[0] - self.b * at[1])

    def perpendicular(self, at):
        return Line(-self.b, self.a, self.b * at[0] - self.a * at[1])


@dataclass(frozen=True)
class Circle:
    center: tuple
    radius_squared: object

    def value(self, at):
        return squared_distance(at, self.center) - self.radius_squared


def line_intersection(first, second):
    determinant = first.a * second.b - second.a * first.b
    if determinant == 0:
        raise ValueError("lines have no unique finite intersection")
    return ((first.b * second.c - second.b * first.c) / determinant,
            (first.c * second.a - second.c * first.a) / determinant)


def line_circle_intersections(line, circle):
    norm_squared = line.a ** 2 + line.b ** 2
    offset = line.value(circle.center)
    foot = (circle.center[0] - line.a * offset / norm_squared,
            circle.center[1] - line.b * offset / norm_squared)
    height_squared = circle.radius_squared - offset ** 2 / norm_squared
    if height_squared < 0:
        return []
    if height_squared == 0:
        return [foot]
    factor = (height_squared / norm_squared).sqrt()
    displacement = (-line.b * factor, line.a * factor)
    return sorted([(foot[0] + displacement[0], foot[1] + displacement[1]),
                   (foot[0] - displacement[0], foot[1] - displacement[1])])


def circle_intersections(first, second):
    dx, dy = subtract(second.center, first.center)
    if dx == 0 and dy == 0:
        raise ValueError("concentric circles have no finite discrete intersection set")
    radical_axis = Line(
        2 * dx, 2 * dy,
        dot(first.center, first.center) - dot(second.center, second.center)
        - first.radius_squared + second.radius_squared,
    )
    return line_circle_intersections(radical_axis, first)


class CubicCurve:
    """The given curve exposes only exact intersection with a constructed line."""

    def __init__(self):
        self.query_count = 0

    def intersect(self, line):
        self.query_count += 1
        ring = PolynomialRing(AA, "x")
        x = ring.gen()
        polynomial = line.b * x ** 3 + line.a * x + line.c
        roots = polynomial.roots(AA, multiplicities=False)
        return [(root, root ** 3) for root in sorted(roots)]


class Construction:
    """Named geometric replay with explicit macro inputs and intersection outputs."""

    def __init__(self):
        self.points = {}
        self.lines = {}
        self.circles = {}
        self.steps = []

    def given_point(self, name, coordinates):
        self.points[name] = point(coordinates)

    def record(self, operation, inputs, outputs):
        self.steps.append({"operation": operation, "inputs": inputs, "outputs": outputs})

    def line(self, name, first, second):
        self.lines[name] = Line.through(self.points[first], self.points[second])
        self.record("line", [first, second], [name])

    def parallel(self, name, at, reference):
        self.lines[name] = self.lines[reference].parallel(self.points[at])
        self.record("parallel", [at, reference], [name])

    def perpendicular(self, name, at, reference):
        self.lines[name] = self.lines[reference].perpendicular(self.points[at])
        self.record("perpendicular", [at, reference], [name])

    def midpoint(self, name, first, second):
        p, q = self.points[first], self.points[second]
        self.points[name] = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        self.record("midpoint", [first, second], [name])

    def circle(self, name, center, radius_start, radius_end):
        radius_squared = squared_distance(self.points[radius_start], self.points[radius_end])
        if radius_squared == 0:
            raise ValueError("a circle needs a positive radius")
        self.circles[name] = Circle(self.points[center], radius_squared)
        self.record("circle_with_transferred_radius", [center, radius_start, radius_end], [name])

    def meet_lines(self, name, first, second):
        self.points[name] = line_intersection(self.lines[first], self.lines[second])
        self.record("line_line_intersection", [first, second], [name])

    def intersections(self, prefix, operation, inputs, coordinates):
        names = [f"{prefix}{index}" for index in range(len(coordinates))]
        for name, at in zip(names, coordinates):
            self.points[name] = point(at)
        self.record(operation, inputs, names)
        return names

    def meet_line_circle(self, prefix, line, circle):
        return self.intersections(prefix, "line_circle_intersection", [line, circle],
                                  line_circle_intersections(self.lines[line], self.circles[circle]))

    def meet_circles(self, prefix, first, second):
        return self.intersections(prefix, "circle_circle_intersection", [first, second],
                                  circle_intersections(self.circles[first], self.circles[second]))

    def select(self, name, candidates, predicate):
        chosen = [candidate for candidate in candidates if predicate(self.points[candidate])]
        if len(chosen) != 1:
            raise ArithmeticError(f"{name} requires exactly one admissible point")
        self.points[name] = self.points[chosen[0]]
        self.record("select", candidates, [name])

    def meet_cubic(self, prefix, line, curve):
        return self.intersections(prefix, "line_cubic_intersection", [line, "given_cubic"],
                                  curve.intersect(self.lines[line]))
