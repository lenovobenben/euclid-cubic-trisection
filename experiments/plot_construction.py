"""Render a static figure from verified exact data. Floats serve display only.

sage -python experiments/plot_construction.py
"""

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc
import numpy as np
from sage.all import AA, QQ, PolynomialRing


ROOT = Path(__file__).resolve().parents[1]
BACKGROUND = "#07101F"
FOREGROUND = "#E8F0F7"
MUTED = "#8397A8"
INPUT = "#F45BFF"
CURRENT = "#FFC857"
AUXILIARY = "#8AC6D9"
RESULT = "#5DE2A5"


def decode(record):
    if isinstance(record, str):
        return AA(QQ(record))
    ring = PolynomialRing(QQ, "x")
    polynomial = ring(record["minimal_polynomial"])
    lower, upper = QQ(record["lower"]), QQ(record["upper"])
    roots = [root for root in polynomial.roots(AA, multiplicities=False) if lower < root < upper]
    if len(roots) != 1:
        raise ArithmeticError("the certificate does not isolate a unique root")
    return roots[0]


def load_points():
    report = json.loads((ROOT / "experiments/results/verification.json").read_text("utf-8"))
    payload = (ROOT / "experiments/results/example.json").read_bytes()
    if not report["valid"] or hashlib.sha256(payload).hexdigest() != report["example_sha256"]:
        raise ArithmeticError("the example differs from the verification report")
    for name, expected in report["source_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ArithmeticError(f"source differs from the verification report: {name}")
    example = json.loads(payload)
    return {name: np.array([float(decode(value)) for value in coordinates])
            for name, coordinates in example["points"].items()}


def annotate(ax, label, at, color, offset=(7, 7)):
    ax.scatter(*at, s=22, color=color, zorder=5)
    ax.annotate(label, at, xytext=offset, textcoords="offset points", color=color, fontsize=12)


def segment(ax, first, second, color, style="-", width=1.6):
    ax.plot([first[0], second[0]], [first[1], second[1]], style, color=color, lw=width)


def main():
    points = load_points()
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12,
                         "text.color": FOREGROUND, "axes.labelcolor": MUTED,
                         "xtick.color": MUTED, "ytick.color": MUTED,
                         "axes.edgecolor": MUTED, "savefig.facecolor": BACKGROUND})
    figure, axes = plt.subplots(1, 3, figsize=(19.2, 7.2), dpi=120, facecolor=BACKGROUND)
    for ax in axes:
        ax.set_facecolor(BACKGROUND)
        ax.set_aspect("equal")
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=10)

    ax = axes[0]
    x = np.linspace(-1.18, 1.18, 600)
    cosine = points["C"][0]
    ax.plot(x, x ** 3, color=INPUT, lw=2, label=r"$y=x^3$")
    ax.plot(x, 0.75 * x + cosine / 4, color=CURRENT, lw=1.8,
            label=r"$L: y=\frac{3}{4}x+\frac{1}{8}$")
    ax.axhline(0, color=MUTED, lw=0.7, alpha=0.6)
    ax.axvline(0, color=MUTED, lw=0.7, alpha=0.6)
    for name in ("k0", "k1"):
        annotate(ax, "", points[name], AUXILIARY)
    annotate(ax, r"$K$", points["K"], RESULT, offset=(9, -1))
    segment(ax, points["K"], points["F"], AUXILIARY, "--", 1)
    ax.text(points["F"][0], -0.17, r"$t>0$", color=RESULT, ha="center")
    ax.set(xlim=(-1.2, 1.3), ylim=(-1.5, 1.6), xlabel=r"$x$", ylabel=r"$y$")
    ax.set_title("Intersect the given cubic", fontsize=17, pad=24)
    legend = ax.legend(loc="upper left", frameon=False, fontsize=12)
    for label in legend.get_texts():
        label.set_color(FOREGROUND)

    ax = axes[1]
    angles = np.linspace(0, np.pi / 2, 250)
    ax.plot(np.cos(angles), np.sin(angles), color=AUXILIARY, lw=1.2)
    ax.axhline(0, color=MUTED, lw=0.7)
    ax.axvline(0, color=MUTED, lw=0.7)
    segment(ax, points["O"], points["P"], INPUT)
    segment(ax, points["O"], points["Q"], RESULT, width=2)
    segment(ax, points["P"], points["C"], MUTED, "--", 1)
    segment(ax, points["Q"], points["F"], CURRENT, "--", 1)
    annotate(ax, r"$P$", points["P"], INPUT)
    annotate(ax, r"$Q$", points["Q"], RESULT)
    annotate(ax, r"$t$", points["F"], CURRENT, offset=(-3, -19))
    annotate(ax, r"$X$", points["X"], AUXILIARY, offset=(7, -2))
    annotate(ax, r"$O$", points["O"], AUXILIARY, offset=(-16, -18))
    ax.text(0.48, -0.09, r"$c$", color=INPUT)
    ax.add_patch(Arc((0, 0), 0.64, 0.64, theta1=0, theta2=20, color=RESULT, lw=1.5))
    ax.text(0.35, 0.035, r"$\theta/3$", color=RESULT, fontsize=13)
    ax.text(0.25, 1.08, r"$Q=(t,\sqrt{1-t^2})$", fontsize=13)
    ax.set(xlim=(-0.12, 1.2), ylim=(-0.15, 1.18), xticks=[], yticks=[])
    ax.spines[["bottom", "left"]].set_visible(False)
    ax.set_title("Lift the positive root", fontsize=17, pad=24)

    ax = axes[2]
    vertex = points["V"]
    angles = np.linspace(0, 2 * np.pi, 300)
    ax.plot(vertex[0] + np.cos(angles), vertex[1] + np.sin(angles),
            color=AUXILIARY, alpha=0.28, lw=1)
    for name, color, offset in (("M", INPUT, (8, 0)), ("N", INPUT, (-20, 3)),
                                ("R1", RESULT, (4, 10)), ("R2", RESULT, (-14, 10))):
        at = points[name]
        segment(ax, vertex, vertex + 1.22 * (at - vertex), color, width=1.8)
        label = {"R1": r"$R_1$", "R2": r"$R_2$"}.get(name, f"${name}$")
        annotate(ax, label, at, color, offset)
    annotate(ax, r"$V$", vertex, AUXILIARY, (-13, -18))
    initial = points["M"] - vertex
    start_angle = np.degrees(np.arctan2(initial[1], initial[0]))
    for index in range(3):
        start = start_angle + 20 * index
        ax.add_patch(Arc(vertex, 0.86, 0.86, theta1=start, theta2=start + 20,
                         color=CURRENT, lw=1.2))
        middle = np.radians(start + 10)
        label_at = vertex + 0.61 * np.array([np.cos(middle), np.sin(middle)])
        ax.text(*label_at, r"$\frac{\theta}{3}$", color=CURRENT, fontsize=13, ha="center", va="center")
    ax.text(vertex[0] - 0.96, vertex[1] - 0.88, r"$\theta=60^\circ$", fontsize=14)
    ax.set(xlim=(vertex[0] - 1.25, vertex[0] + 1.25),
           ylim=(vertex[1] - 1.18, vertex[1] + 1.35), xticks=[], yticks=[])
    ax.spines[["bottom", "left"]].set_visible(False)
    ax.set_title("Restore both original-position rays", fontsize=17, pad=24)

    figure.suptitle(r"$4t^3-3t=\cos\theta$", fontsize=24, y=0.96)
    figure.subplots_adjust(left=0.045, right=0.98, bottom=0.1, top=0.82, wspace=0.27)
    destination = ROOT / "docs/figures/construction.png"
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=120)
    plt.close(figure)
    print(destination.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
