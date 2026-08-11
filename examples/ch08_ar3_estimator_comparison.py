"""Chapter 8, Table 8.1 — three estimators for an AR(3) under contamination.

Python port of ``ar3.R``.

A simulated AR(3) with known coefficients (4/3, -5/6, 1/6), fitted three ways at
three contamination levels (0%, 5%, 10% equispaced additive outliers of size 4):

* least squares on the lagged regression — the baseline;
* ``lmrobdetMM`` on the same lagged regression — robust *regression*, which
  handles outliers in the response but still uses contaminated lagged values as
  predictors;
* ``arima.rob`` — the filtered tau estimator, which is built for the time-series
  structure and cleans the predictors as well.

That middle row is the interesting one. Robust regression helps, but a lagged
regression feeds every outlier back in as a covariate, so it cannot fully
recover — which is the argument for a time-series-specific estimator.

R packages required: RobStatTM and ``robustarima``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from _common import require_r_packages, run, section
from _ts import additive_outliers, arima_sim

import robstattm_py as rpm

SEED = 600
N = 200
N_INNOV = 300
PHI = (4 / 3, -5 / 6, 1 / 6)
SPIKE = 4.0


def main() -> None:
    section("Chapter 8, Table 8.1 — AR(3) under increasing contamination")

    require_r_packages("robustarima")

    clean = arima_sim(seed=SEED, n=N, n_innov=N_INNOV, ar=PHI)
    print(f"  true phi = ({PHI[0]:.4f}, {PHI[1]:.4f}, {PHI[2]:.4f}), n = {N}")

    series = {
        "no outliers": clean,
        "5% outliers": additive_outliers(clean, every=20, size=SPIKE),
        "10% outliers": additive_outliers(clean, every=10, size=SPIKE),
    }

    cont = rpm.lmrobdet_control(bb=0.5, efficiency=0.85, family="bisquare")

    print(f"\n  {'series':<16}{'estimator':<14}"
          f"{'phi1':>10}{'phi2':>10}{'phi3':>10}{'error':>10}")
    print(f"  {'':<16}{'truth':<14}"
          f"{PHI[0]:>10.4f}{PHI[1]:>10.4f}{PHI[2]:>10.4f}{0.0:>10.4f}")

    for label, x in series.items():
        lagged = _lagged_frame(x, order=3)

        ls = np.linalg.lstsq(
            np.column_stack([np.ones(len(lagged)), lagged[["l1", "l2", "l3"]]]),
            lagged["y"].to_numpy(),
            rcond=None,
        )[0][1:]

        mm = rpm.lmrobdet_mm("y ~ l1 + l2 + l3", data=lagged, control=cont)
        mm_phi = np.asarray(mm.coefficients, dtype=float)[1:]

        tau = rpm.arima_rob("x ~ 1", data=pd.DataFrame({"x": x}), p=3)
        tau_phi = np.asarray(tau.ar, dtype=float)

        for estimator, phi in (
            ("least squares", ls),
            ("lmrobdetMM", mm_phi),
            ("arima.rob tau", tau_phi),
        ):
            error = float(np.linalg.norm(np.asarray(phi) - np.array(PHI)))
            print(
                f"  {label:<16}{estimator:<14}"
                + "".join(f"{float(p):>10.4f}" for p in phi)
                + f"{error:>10.4f}"
            )
        print()

    print(
        "  Read the error column down each block. With no outliers all three\n"
        "  agree. At 5% the ordering is the expected one — least squares worst,\n"
        "  robust regression better, the tau estimator best.\n"
        "\n"
        "  At 10% the middle row is the one to look at: lmrobdetMM is no better\n"
        "  than least squares. That is not a failure of robust regression; it is\n"
        "  the lagged design defeating it. Every outlier appears three times as a\n"
        "  *predictor* as well as once as a response, and downweighting a bad\n"
        "  response cannot undo a bad covariate. Only the filtered estimator,\n"
        "  which cleans the series before using it on either side, holds up —\n"
        "  which is the argument for treating a time series as a time series\n"
        "  rather than as a regression that happens to have lags in it."
    )


def _lagged_frame(x: np.ndarray, *, order: int) -> pd.DataFrame:
    """Build the lagged design ``ar3.R`` regresses on: x[t] against x[t-1..t-p]."""
    return pd.DataFrame(
        {
            "y": x[order:],
            **{f"l{k}": x[order - k : len(x) - k] for k in range(1, order + 1)},
        }
    )


if __name__ == "__main__":
    run(main)
