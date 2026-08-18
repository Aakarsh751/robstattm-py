"""Chapter 8, Example 8.4, identifying an MA(1) under contamination (Figs 8.9-8.10).

Python port of ``identMA1.R``.

The MA counterpart of ``ch08_identar2_identification.py``, and a harder case:
an MA(1)'s signature is a single non-zero autocorrelation at lag 1 and nothing
beyond it. Additive outliers shrink that one informative value toward zero,
which is precisely the direction that makes the series look like white noise,
so the failure mode is not choosing the wrong order but concluding there is no
structure at all.

The outliers here are larger than in the AR(2) example (mean 6 rather than 4),
which makes the effect correspondingly starker.

R packages required: RobStatTM and ``robustarima``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from _common import require_r_packages, run, section, table
from _ts import acf, arima_sim, rnorm, runif

import robstattm_py as rpm

SEED = 600
N = 200
N_INNOV = 300
THETA = 0.8
LAGS = 10


def main() -> None:
    section("Chapter 8, Example 8.4, identifying an MA(1) with 10% outliers")

    require_r_packages("robustarima")

    clean = arima_sim(seed=SEED, n=N, n_innov=N_INNOV, ma=(THETA,))
    contaminated, n_outliers = _contaminate(clean)
    print(f"  true model: MA(1), theta = {THETA}")
    print(f"  {n_outliers} additive outliers (mean size 6) in {N} observations")

    fit = rpm.arima_rob("x ~ 1", data=pd.DataFrame({"x": contaminated}), auto_ar=True)
    filtered = np.asarray(fit.y_robust, dtype=float)

    section("Figure 8.10, sample autocorrelations")
    clean_acf = acf(clean, LAGS)
    dirty_acf = acf(contaminated, LAGS)
    filtered_acf = acf(filtered, LAGS)

    print(f"\n  {'lag':<6}{'clean':>12}{'contaminated':>16}{'filtered':>12}")
    for k in range(LAGS):
        print(
            f"  {k + 1:<6}{clean_acf[k]:>12.4f}"
            f"{dirty_acf[k]:>16.4f}{filtered_acf[k]:>12.4f}"
        )

    section("The lag-1 autocorrelation, the whole signature of an MA(1)")
    # For an MA(1) the theoretical lag-1 autocorrelation is theta / (1 + theta^2).
    theoretical = THETA / (1 + THETA**2)
    table(
        "rho(1)",
        {
            "theoretical": theoretical,
            "clean series": float(clean_acf[0]),
            "contaminated": float(dirty_acf[0]),
            "filtered": float(filtered_acf[0]),
        },
    )
    retained = float(dirty_acf[0] / clean_acf[0])
    recovered = float(filtered_acf[0] / clean_acf[0])
    print(
        f"\n  Contamination retains only {retained:.0%} of the clean lag-1\n"
        f"  autocorrelation; filtering recovers {recovered:.0%} of it. An MA(1)\n"
        "  carries all of its structure in this one number, so shrinking it is\n"
        "  the same as erasing the model, the contaminated column would be read\n"
        "  as 'no meaningful dependence'."
    )

    section("Beyond lag 1 there should be nothing")
    table(
        "max |rho(k)| for k >= 2",
        {
            "clean": float(np.abs(clean_acf[1:]).max()),
            "contaminated": float(np.abs(dirty_acf[1:]).max()),
            "filtered": float(np.abs(filtered_acf[1:]).max()),
        },
    )


def _contaminate(clean: np.ndarray) -> tuple[np.ndarray, int]:
    """Plant sign-randomised additive outliers, as ``identMA1.R`` does."""
    magnitude = np.where(runif(N) > 0.1, 0.0, rnorm(N, 6.0, 1.0))
    signs = np.sign(runif(N) * 2.0 - 1.0)
    shift = signs * magnitude
    return clean + shift, int((shift != 0).sum())


if __name__ == "__main__":
    run(main)
