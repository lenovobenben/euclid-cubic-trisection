"""Portable exact real-algebraic certificates with rational isolating intervals."""

from sage.all import AA, QQ

import sage_compat  # Exact certificate encoding also uses the pinned backend.


def exact_record(value):
    value = AA(value)
    if value in QQ:
        return str(QQ(value))
    polynomial = value.minpoly()
    bits = 64
    while True:
        denominator = 2 ** bits
        lower = QQ((value * denominator).floor()) / denominator
        upper = lower + QQ(1) / denominator
        # An irrational minimal polynomial has no rational endpoint roots.
        if polynomial.number_of_roots_in_interval(lower, upper) == 1:
            return {"minimal_polynomial": str(polynomial),
                    "lower": str(lower), "upper": str(upper)}
        bits *= 2


def point_record(at):
    return [exact_record(value) for value in at]
