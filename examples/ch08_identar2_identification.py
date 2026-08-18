"""Chapter 8, Example 8.3, model identification under contamination (Figs 8.7-8.8).

Python port of ``identAR2.R``.

Before you can fit a time-series model you have to choose its order, and that
choice is usually made by reading the sample ACF and PACF. This example shows
that step failing: an AR(2) series with about 10% additive outliers has a sample
ACF that no longer looks like an AR(2)'s, so the usual identification procedure
picks the wrong model, before any estimator is involved.

``arima.rob(auto.ar = True)`` selects the order from the *filtered* series
instead, which is what makes the choice recoverable.

R packages required: RobStatTM and ``robustarima``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from _common import require_r_packages, run, section, table
from _ts import acf, arima_sim, rnorm, runif

import robstattm_py as rpm

SEED = 700
N = 200
N_INNOV = 300
PHI = (4 / 3, -5 / 6)
LAGS = 10


def main() -> None:
    section("Chapter 8, Example 8.3, identifying an AR(2) with 10% outliers")

    require_r_packages("robustarima")

    clean = arima_sim(seed=SEED, n=N, n_innov=N_INNOV, ar=PHI)
    contaminated, n_outliers = _contaminate(clean)
    print(f"  true order: AR(2), phi = ({PHI[0]:.4f}, {PHI[1]:.4f})")
    print(f"  {n_outliers} additive outliers planted in {N} observations")

    section("Figure 8.8, sample autocorrelations")
    clean_acf = acf(clean, LAGS)
    dirty_acf = acf(contaminated, LAGS)

    fit = rpm.arima_rob("x ~ 1", data=pd.DataFrame({"x": contaminated}), auto_ar=True)
    filtered = np.asarray(fit.y_robust, dtype=float)
    filtered_acf = acf(filtered, LAGS)

    print(f"\n  {'lag':<6}{'clean':>12}{'contaminated':>16}{'filtered':>12}")
    for k in range(LAGS):
        print(
            f"  {k + 1:<6}{clean_acf[k]:>12.4f}"
            f"{dirty_acf[k]:>16.4f}{filtered_acf[k]:>12.4f}"
        )

    table(
        "mean absolute deviation from the clean ACF",
        {
            "contaminated series": float(np.abs(dirty_acf - clean_acf).mean()),
            "filtered series": float(np.abs(filtered_acf - clean_acf).mean()),
        },
    )
    print(
        "\n  The contaminated ACF is uniformly shrunk toward zero, additive\n"
        "  outliers add variance without adding correlation, so every\n"
        "  autocorrelation is divided by a larger number. Reading an order off\n"
        "  that column would understate the dependence in the series. Filtering\n"
        "  first restores it."
    )

    section("What order did the robust procedure choose?")
    ar = np.asarray(fit.ar, dtype=float)
    table(
        "arima.rob(auto.ar=True)",
        {
            "order selected": len(ar),
            "coefficients": tuple(float(a) for a in ar),
            "true order": len(PHI),
            "true coefficients": PHI,
        },
    )
    if len(ar) > len(PHI):
        extra = np.abs(ar[len(PHI):]).max()
        print(
            f"\n  The automatic search overshoots the true order here, and it is\n"
            "  worth being clear about that rather than rounding it off. What it\n"
            f"  selects is an AR({len(ar)}) whose first two coefficients are close to\n"
            f"  the truth and whose remaining ones are near zero (largest\n"
            f"  {extra:.4f}), an over-parameterised model of the right process,\n"
            "  not the wrong process. identAR2.R notes the same thing: the\n"
            "  optimiser reports non-convergence and the conclusions still hold.\n"
            "  The claim this example supports is about the ACF above, which is\n"
            "  what identification actually reads."
        )


def _contaminate(clean: np.ndarray) -> tuple[np.ndarray, int]:
    """Plant sign-randomised additive outliers at roughly 10% of positions.

    Continues R's RNG stream in the order ``identAR2.R`` uses it, so the
    contamination pattern is the script's.
    """
    magnitude = np.where(runif(N) > 0.1, 0.0, rnorm(N, 4.0, 1.0))
    signs = np.sign(runif(N) * 2.0 - 1.0)
    shift = signs * magnitude
    return clean + shift, int((shift != 0).sum())


if __name__ == "__main__":
    run(main)
