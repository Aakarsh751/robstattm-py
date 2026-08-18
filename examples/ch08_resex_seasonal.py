"""Chapter 8, Example 8.6, seasonal ARIMA on real data (Figs 8.12-8.13, Table 8.5).

Python port of ``resex.R``.

89 monthly residential telephone extension counts. Unlike the rest of Chapter 8
this is real data, and the outliers are real too: two months in which a
strike-related backlog was cleared, producing counts unlike anything else in the
series.

An AR(2) is fitted to the seasonally differenced series (``sd = 1``,
``sfreq = 12``) two ways: by the filtered tau estimator, and by ordinary least
squares on the differenced series exactly as ``resex.R`` does it. The two
estimates of the same coefficients differ substantially, and the innovation
quantiles show which one is describing the bulk of the data.

R packages required: RobStatTM and ``robustarima``.
"""
from __future__ import annotations

import numpy as np
from _common import figure, require_r_packages, run, section, table

import robstattm_py as rpm

SEASON = 12
ORDER = 2


def main() -> None:
    section("Chapter 8, Example 8.6, residential extensions")

    require_r_packages("robustarima")

    resex = rpm.datasets.resex()
    y = resex["resex"].to_numpy(dtype=float)
    n = len(y)
    print(f"  {n} monthly observations, seasonal period {SEASON}")

    # -- Filtered tau on the seasonally differenced series -----------------
    fit = rpm.arima_rob("resex ~ 1", data=resex, p=ORDER, sd=1, sfreq=SEASON)
    ar_tau = np.asarray(fit.ar, dtype=float)
    mean_tau = float(np.asarray(fit.regcoef, dtype=float).ravel()[0])
    intercept_tau = mean_tau * (1.0 - ar_tau.sum())

    # -- Least squares on the same differenced series ----------------------
    # resex.R differences by hand: sresx <- resex[13:89] - resex[1:77].
    differenced = y[SEASON:] - y[: n - SEASON]
    ar_ls, intercept_ls, ls_resid = _ar_least_squares(differenced, order=ORDER)

    section("Table 8.5, AR(2) coefficients of the differenced series")
    print(f"\n  {'estimator':<18}{'AR(1)':>12}{'AR(2)':>12}{'intercept':>14}")
    print(
        f"  {'filtered tau':<18}{ar_tau[0]:>12.4f}{ar_tau[1]:>12.4f}"
        f"{intercept_tau:>14.4f}"
    )
    print(
        f"  {'least squares':<18}{ar_ls[0]:>12.4f}{ar_ls[1]:>12.4f}"
        f"{intercept_ls:>14.4f}"
    )
    table("mean of the differenced series (tau)", {"mean": mean_tau})

    section("Figure 8.13, sorted absolute innovations")
    tau_innov = np.sort(np.abs(np.asarray(fit.innov, dtype=float)[14:89]))
    ls_innov = np.sort(np.abs(ls_resid))
    k = min(len(tau_innov), len(ls_innov), 72)
    print(f"\n  {'quantile':<12}{'tau':>14}{'least squares':>16}")
    for q in (0.25, 0.5, 0.75, 0.9):
        i = int(q * k)
        print(f"  {q:<12.2f}{tau_innov[i]:>14.2f}{ls_innov[i]:>16.2f}")
    table(
        f"sum over the {k} smallest",
        {"tau": float(tau_innov[:k].sum()), "least squares": float(ls_innov[:k].sum())},
    )
    print(
        "\n  The tau fit's innovations are smaller across the body of the\n"
        "  distribution. Both models have the same number of parameters and see\n"
        "  the same data; the difference is that least squares spent some of its\n"
        "  fit on two months that will not recur."
    )

    section("Figure 8.12, which observations did the filter clean?")
    robust_series = np.asarray(fit.y_robust, dtype=float)
    change = np.abs(y - robust_series)
    worst = np.argsort(change)[::-1][:5]
    table(
        "largest filter adjustment (1-based index)",
        {str(int(i) + 1): (float(y[i]), float(robust_series[i])) for i in worst},
    )
    print("  (columns: observed, filtered)")

    rpm.plot.location_scale(
        rpm.loc_scale_m(np.diff(y, n=1)),
        np.diff(y, n=1),
        title="Resex, first differences (Figure 8.12)",
        save=figure("ch08_resex_differences"),
    )


def _ar_least_squares(
    x: np.ndarray, *, order: int
) -> tuple[np.ndarray, float, np.ndarray]:
    """Least-squares AR(``order``) fit, ``resex.R``'s ``lm`` on lagged columns."""
    y = x[order:]
    design = np.column_stack(
        [np.ones(len(y))] + [x[order - k : len(x) - k] for k in range(1, order + 1)]
    )
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    return coef[1:], float(coef[0]), y - design @ coef


if __name__ == "__main__":
    run(main)
