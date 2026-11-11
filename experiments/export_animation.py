"""Export display coordinates from the independently checked construction.

Run verify.py --write before this script. The exact example must reproduce
the saved certificate byte for byte before its coordinates are converted.
"""

import hashlib
import json
from pathlib import Path

from sage.all import QQ

from fixtures import fixtures
from verify import atomic_write, encoded_json, example_record, require, verify_fixture


ROOT = Path(__file__).resolve().parents[1]


def main():
    report = json.loads((ROOT / "experiments/results/verification.json").read_text("utf-8"))
    require(report["valid"], "the saved verification report must be valid")
    for name, expected in report["source_sha256"].items():
        require(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected,
                f"source changed since verification: {name}")
    fixture = next(item for item in fixtures() if item["name"] == "60_degrees/translated_rotated_ccw")
    result, certificate = verify_fixture(fixture)
    exact_bytes = encoded_json(example_record(result))
    require(exact_bytes == (ROOT / "experiments/results/example.json").read_bytes(),
            "the reconstructed exact example must match the saved example")
    require(hashlib.sha256(exact_bytes).hexdigest() == report["example_sha256"], "exact example hash")
    g = result.construction
    samples = []
    for index in range(-110, 119):
        x = QQ(index) / 100
        y = x ** 3
        require(y - x ** 3 == 0, "cubic display sample incidence")
        samples.append([float(x), float(y)])
    data = {
        "format_version": 1,
        "example_name": fixture["name"],
        "input_angle_degrees": 60,
        "source_example_sha256": report["example_sha256"],
        "source_sha256": report["source_sha256"],
        "points": {name: list(map(float, at)) for name, at in g.points.items()},
        "lines": {name: list(map(float, (line.a, line.b, line.c))) for name, line in g.lines.items()},
        "circles": {name: {"center": list(map(float, circle.center)),
                           "radius": float(circle.radius_squared.sqrt())}
                    for name, circle in g.circles.items()},
        "steps": g.steps,
        "cubic_samples": samples,
        "cubic_query_count": result.cubic_query_count,
        "certificate": certificate,
    }
    payload = encoded_json(data)
    path = ROOT / "animations/trisection/geometry.json"
    atomic_write(path, payload)
    digest = hashlib.sha256(payload).hexdigest()
    atomic_write(path.with_suffix(".sha256"), (digest + "\n").encode("ascii"))
    print(json.dumps({"path": path.relative_to(ROOT).as_posix(),
                      "sha256": digest,
                      "verified_cubic_samples": len(samples)}, indent=2))


if __name__ == "__main__":
    main()
