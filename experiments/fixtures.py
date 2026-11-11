"""Algebraic acute inputs, including irreducible and limiting families."""

from sage.all import AA, QQ


def fixtures():
    epsilon = QQ(1) / 10 ** 30
    extreme_epsilon = QQ(1) / 10 ** 100
    cosines = [
        ("60_degrees", AA(1) / 2),
        ("45_degrees", AA(2).sqrt() / 2),
        ("30_degrees", AA(3).sqrt() / 2),
        ("rational_cosine_3_5", AA(3) / 5),
        ("rational_cosine_4_5", AA(4) / 5),
        ("rational_cosine_5_13", AA(5) / 13),
        ("rational_output_7_8", AA(7) / 128),
        ("quadratic_output_sqrt15_4", 3 * AA(15).sqrt() / 16),
        ("near_right_angle", AA(epsilon)),
        ("near_zero_angle", AA(1 - epsilon)),
        ("extreme_near_right_angle", AA(extreme_epsilon)),
        ("extreme_near_zero_angle", AA(1 - extreme_epsilon)),
    ]
    frames = [
        ("standard_ccw", (0, 0), (1, 0), 1, 1, 1),
        ("translated_rotated_ccw", (7, -11), (QQ(3) / 5, QQ(4) / 5), 1, 2, 7),
        ("translated_rotated_cw", (-3, 5), (-QQ(5) / 13, QQ(12) / 13), -1, 5, 3),
        ("tiny_ray_markers_cw", (1, 0), (0, -1), -1, epsilon, 2 * epsilon),
    ]
    for name, cosine in cosines:
        sine = (1 - cosine ** 2).sqrt()
        for frame, vertex, unit, orientation, first_scale, second_scale in frames:
            ux, uy = map(AA, unit)
            vx = cosine * ux - orientation * sine * uy
            vy = cosine * uy + orientation * sine * ux
            vertex = tuple(map(AA, vertex))
            yield {
                "name": f"{name}/{frame}",
                "vertex": vertex,
                "first": (vertex[0] + first_scale * ux, vertex[1] + first_scale * uy),
                "second": (vertex[0] + second_scale * vx, vertex[1] + second_scale * vy),
                "cosine": cosine,
            }


def invalid_fixtures():
    return [
        ("zero_first_ray", (0, 0), (0, 0), (1, 1)),
        ("zero_second_ray", (0, 0), (1, 1), (0, 0)),
        ("both_zero", (2, 3), (2, 3), (2, 3)),
        ("coincident_rays", (0, 0), (1, 0), (2, 0)),
        ("opposite_rays", (0, 0), (1, 0), (-1, 0)),
        ("right_ccw", (0, 0), (1, 0), (0, 1)),
        ("right_cw", (0, 0), (1, 0), (0, -1)),
        ("obtuse_ccw", (0, 0), (1, 0), (-1, 1)),
        ("obtuse_cw", (0, 0), (1, 0), (-1, -1)),
    ]
