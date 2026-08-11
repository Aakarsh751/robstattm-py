"""Chapter 5, Example 5.5 — the exact-fit property on synthetic data.

Python port of ``ExactFit.R``.

100 points on the line ``y = x`` with a little noise, and 50 points on
``y = -x``. A third of the data is "wrong", which is well inside an
MM-estimator's 50% breakdown point but far outside what least squares can
survive. Least squares splits the difference and describes neither group; the
MM fit recovers the majority line almost exactly.

The data are generated with R's RNG under ``set.seed(1003)``, matching the R
script, so the numbers below are reproducible and comparable with it. Generating
them with numpy instead would give a different sample from the same
distribution — the conclusion would hold, but the printed values would not
line up with the R script's.

R packages required: RobStatTM only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from _common import figure, ols, run, section, table

import robstattm_py as rpm

SEED = 1003
N_GOOD = 100
N_BAD = 50
SIGMA = 0.1


def simulate() -> pd.DataFrame:
    """Reproduce ``ExactFit.R``'s data set, drawing from R's RNG under its seed.

    ``rpm.set_seed`` seeds the R generator this package is already talking to,
    so ``numpy.random`` is deliberately not used here — the point is to land on
    the same sample the R script does.
    """
    rpm.set_seed(SEED)
    from robstattm_py._r import r

    ro = r()
    # Drawn in exactly the order ExactFit.R draws them; the RNG is sequential,
    # so re-ordering these calls would silently produce a different data set.
    rr = np.asarray(ro.r(f"rnorm({N_BAD})"), dtype=float)
    x1 = np.sort(np.asarray(ro.r(f"rnorm({N_GOOD})"), dtype=float))
    x2 = np.sort(rr) * 2
    y1 = x1 + SIGMA * np.asarray(ro.r(f"rnorm({N_GOOD})"), dtype=float)
    y2 = -x2 + SIGMA * np.asarray(ro.r(f"rnorm({N_BAD})"), dtype=float)

    return pd.DataFrame({"x": np.concatenate([x1, x2]), "y": np.concatenate([y1, y2])})


def main() -> None:
    section("Chapter 5, Example 5.5 — exact fit")

    data = simulate()
    x = data["x"].to_numpy()
    y = data["y"].to_numpy()
    print(
        f"  {N_GOOD} points on y = x (sigma {SIGMA}), "
        f"{N_BAD} points on y = -x — {N_BAD / (N_GOOD + N_BAD):.0%} contamination"
    )

    ls = ols(x, y)
    # ExactFit.R takes lmrobdetMM's defaults: family "mopt", efficiency 0.95.
    mm = rpm.lmrobdet_mm("y ~ x", data=data)

    section("Recovered lines (truth for the majority: intercept 0, slope 1)")
    table(
        "intercept, slope",
        {
            "least squares": ls,
            "MM (defaults)": tuple(float(c) for c in mm.coefficients),
            "truth (majority)": (0.0, 1.0),
        },
    )
    table(
        "distance from the majority line",
        {
            "least squares": float(np.hypot(ls[0], ls[1] - 1.0)),
            "MM (defaults)": float(
                np.hypot(mm.coefficients[0], mm.coefficients[1] - 1.0)
            ),
        },
    )

    section("Did the MM fit isolate the contaminated third?")
    weights = mm.weights().to_numpy()
    # The last N_BAD rows are the planted outliers, by construction.
    is_planted = np.arange(len(weights)) >= N_GOOD
    table(
        "mean robustness weight",
        {
            "good points": float(weights[~is_planted].mean()),
            "planted outliers": float(weights[is_planted].mean()),
        },
    )
    table(
        "points given zero weight",
        {
            "good points": int((weights[~is_planted] == 0).sum()),
            "planted outliers": int((weights[is_planted] == 0).sum()),
        },
    )

    rpm.plot.scatter_with_fit(
        mm,
        x="x",
        show_ols=True,
        title="Exact fit — MM recovers the majority line, LS does not",
        save=figure("ch05_exactfit"),
    )


if __name__ == "__main__":
    run(main)
