"""Portable exact real-algebraic certificates with rational isolating intervals."""

from sage.all import AA, QQ


def exact_record(value):
    value = AA(value)
    if value in QQ:
        return str(QQ(value))
    polynomial = value.minpoly()
    roots = polynomial.roots(AA, multiplicities=False)
    bits = 64
    while True:
        denominator = 2 ** bits
        lower = QQ((value * denominator).floor()) / denominator
        upper = lower + QQ(1) / denominator
        if sum(lower < root < upper for root in roots) == 1:
            return {"minimal_polynomial": str(polynomial),
                    "lower": str(lower), "upper": str(upper)}
        bits *= 2


def point_record(at):
    return [exact_record(value) for value in at]
