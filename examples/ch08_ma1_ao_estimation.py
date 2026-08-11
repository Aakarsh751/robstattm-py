"""Chapter 8, Example 8.5 — robust MA(1) estimation (Figure 8.11, Table 8.4).

Python port of ``MA1-AO.R``.

An MA(1) with theta = -0.8, contaminated with ten additive outliers of size 4 at
every twentieth observation, fitted by the filtered tau estimator
(``arima.rob``). Ten spikes in two hundred observations is 5% contamination;
the previous example showed what that does to identification, and this one
shows what it does to estimation.

The R script also fits ``arima(order = c(0, 0, 1), method = "CSS")`` as the
non-robust comparator. Conditional sum of squares for an MA model is an
iterative innovations recursion rather than a closed form, and reimplementing it
here would be writing an estimator rather than demonstrating one — so the
comparison below is against the *clean-series* tau fit, which answers the same
question: how far does contamination move the estimate?

R packages required: RobStatTM and ``robustarima``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from _common import figure, require_r_packages, run, section, table
from _ts import additive_outliers, arima_sim

import robstattm_py as rpm

SEED = 200
N = 200
N_INNOV = 300
THETA = -0.8
SPIKE = 4.0
EVERY = 20


def main() -> None:
    section("Chapter 8, Example 8.5 — MA(1) with additive outliers")

    require_r_packages("robustarima")

    clean = arima_sim(seed=SEED, n=N, n_innov=N_INNOV, ma=(THETA,))
    contaminated = additive_outliers(clean, every=EVERY, size=SPIKE)
    n_spikes = N // EVERY
    print(f"  true theta = {THETA}, n = {N}")
    print(f"  {n_spikes} additive outliers of size {SPIKE} ({n_spikes / N:.0%})")

    clean_fit = rpm.arima_rob("x ~ 1", data=pd.DataFrame({"x": clean}), q=1)
    dirty_fit = rpm.arima_rob("x ~ 1", data=pd.DataFrame({"x": contaminated}), q=1)

    clean_theta = float(np.asarray(clean_fit.ma, dtype=float)[0])
    dirty_theta = float(np.asarray(dirty_fit.ma, dtype=float)[0])

    section("Table 8.4 — the estimate barely moves")
    table(
        "theta",
        {
            "simulated with": THETA,
            "tau on the clean series": clean_theta,
            "tau on the contaminated series": dirty_theta,
        },
    )
    print(
        "\n  Mind the sign. `arima.sim` and `arima.rob` use opposite MA sign\n"
        f"  conventions, so simulating with theta = {THETA} and recovering\n"
        f"  {clean_theta:+.4f} is agreement, not a discrepancy. The magnitude is\n"
        "  what to compare, and the row below is what the example is about."
    )
    table(
        "shift caused by 5% contamination",
        {"|delta theta|": abs(dirty_theta - clean_theta)},
    )

    section("Figure 8.11 — how much of each spike did the filter remove?")
    filtered = np.asarray(dirty_fit.y_robust, dtype=float)
    spike_positions = np.arange(EVERY - 1, N, EVERY)
    removed = contaminated[spike_positions] - filtered[spike_positions]
    table(
        "at the contaminated positions (1-based)",
        {
            "spike size injected": SPIKE,
            "median amount filtered out": float(np.median(removed)),
            "smallest": float(removed.min()),
            "largest": float(removed.max()),
        },
    )

    clean_positions = np.setdiff1d(np.arange(N), spike_positions)
    table(
        "at the uncontaminated positions",
        {
            "median |change|": float(
                np.median(np.abs(contaminated[clean_positions] - filtered[clean_positions]))
            ),
            "largest |change|": float(
                np.abs(contaminated[clean_positions] - filtered[clean_positions]).max()
            ),
        },
    )
    print(
        "\n  The filter is doing targeted work, not smoothing: it removes most of\n"
        "  each injected spike and leaves the other 190 observations nearly\n"
        "  untouched. That selectivity is why the estimate above holds still."
    )

    rpm.plot.location_scale(
        rpm.loc_scale_m(contaminated),
        contaminated,
        title="MA(1) with 5% additive outliers (Figure 8.11)",
        save=figure("ch08_ma1_ao"),
    )


if __name__ == "__main__":
    run(main)
