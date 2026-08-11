"""Chapter 8 — additive versus innovation outliers in an AR(1) series (Fig 8.6).

Python port of ``ar1.R``.

Two kinds of contamination look similar on a plot and behave completely
differently:

* an **additive outlier** perturbs the observation only. The underlying process
  is untouched, so the series returns to normal immediately — but the
  *estimated* AR coefficient is badly biased, because each spike creates a pair
  of consecutive observations that look uncorrelated.
* an **innovation outlier** perturbs the process itself. The shock propagates
  forward through the AR recursion, so the visible disturbance is longer-lived,
  yet the estimated coefficient is barely affected — the observation is
  unusual, but it is a genuine draw from the model.

This example only generates and characterises the three series (Figure 8.6);
``ch08_ar3_estimator_comparison.py`` is where the estimators are compared.

R packages required: RobStatTM only.
"""
from __future__ import annotations

import numpy as np
from _common import figure, ols, run, section, table
from _ts import additive_outliers, arima_sim, rnorm

import robstattm_py as rpm

SEED = 1000
N = 100
N_INNOV = 200
PHI = 0.9
SPIKE = 4.0
EVERY = 10
IO_AT = 50  # 1-based index of the innovation outlier


def main() -> None:
    section("Chapter 8, Figure 8.6 — additive vs innovation outliers, AR(1)")

    clean = arima_sim(seed=SEED, n=N, n_innov=N_INNOV, ar=(PHI,))
    with_ao = additive_outliers(clean, every=EVERY, size=SPIKE)
    with_io = _innovation_outlier(clean)

    print(f"  AR(1) with phi = {PHI}, n = {N}")
    print(f"  additive:   +{SPIKE} at every {EVERY}th observation ({N // EVERY} spikes)")
    print(f"  innovation: a single shock of +10 injected at observation {IO_AT}")

    section("What the contamination does to the estimated phi")
    table(
        "lag-1 least squares (the naive estimate)",
        {
            "clean series": _phi_ls(clean),
            "additive outliers": _phi_ls(with_ao),
            "innovation outlier": _phi_ls(with_io),
            "true phi": PHI,
        },
    )
    print(
        "\n  Ten additive outliers in a hundred observations move the estimate\n"
        "  far more than one innovation outlier does — even though the additive\n"
        "  spikes leave the underlying process intact and the innovation shock\n"
        "  does not. Visual size is a poor guide to how much damage an outlier\n"
        "  does; what matters is whether it breaks the model's correlation\n"
        "  structure."
    )

    section("Robust scale of each series")
    table(
        "M-scale (bisquare)",
        {
            "clean": rpm.m_scale(clean),
            "additive": rpm.m_scale(with_ao),
            "innovation": rpm.m_scale(with_io),
        },
    )

    rpm.plot.location_scale(
        rpm.loc_scale_m(with_ao),
        with_ao,
        title="AR(1) with 10% additive outliers (Figure 8.6)",
        save=figure("ch08_ar1_additive"),
    )


def _innovation_outlier(clean: np.ndarray) -> np.ndarray:
    """Rebuild the tail of the series after a single large innovation.

    Follows ``ar1.R``: keep the first 49 observations, replace observation 50
    with ``phi * x[49] + 10``, then propagate the AR recursion forward with
    fresh innovations. The shock persists because the recursion carries it, not
    because it is re-applied.
    """
    out = clean.copy()
    out[IO_AT - 1] = PHI * out[IO_AT - 2] + 10.0
    innovations = rnorm(N - IO_AT)
    for i in range(IO_AT, N):
        out[i] = PHI * out[i - 1] + innovations[i - IO_AT]
    return out


def _phi_ls(series: np.ndarray) -> float:
    """Least-squares AR(1) coefficient: regress x[t] on x[t-1]."""
    return ols(series[:-1], series[1:])[1]


if __name__ == "__main__":
    run(main)
