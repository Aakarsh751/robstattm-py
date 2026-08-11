"""Chapter 4, Example 4.1 — M-regression on the shock data (Figures 4.1, 4.3).

Python port of ``shock.R``.

Sixteen observations of average response time against number of shocks. Three
of them (1, 2 and 4) are outliers, and they are enough to tilt the least-squares
line away from the other thirteen points. The example fits, on the same axes:

* least squares on everything,
* least squares with observations 1, 2 and 4 deleted — the answer you would get
  if you already knew which points to distrust,
* an M-estimator (``lmrobM``), which finds that answer without being told.

The R script also draws an L1 (quantile-regression) line via ``quantreg::rq``.
There is no robust-quantile wrapper in this package and adding one would be out
of scope, so the L1 fit comes from ``_common.l1_line`` — it is a comparator in
this figure, not one of the estimators under study.

R packages required: RobStatTM only.
"""
from __future__ import annotations

import numpy as np
from _common import figure, l1_line, ols, run, section, table

import robstattm_py as rpm


def main() -> None:
    section("Chapter 4, Example 4.1 — shock data")

    shock = rpm.datasets.shock()
    x = shock["n_shocks"].to_numpy(dtype=float)
    y = shock["time"].to_numpy(dtype=float)

    # The book's control: bisquare, 85% efficiency. lmrobdet.control's current
    # defaults are mopt/0.95; these are kept so the numbers match the printed
    # example.
    cont = rpm.lmrobm_control(bb=0.5, efficiency=0.85, family="bisquare")

    ls_all = ols(x, y)
    # Observations 1, 2 and 4 in the book's 1-based numbering.
    keep = np.ones(len(x), dtype=bool)
    keep[[0, 1, 3]] = False
    ls_clean = ols(x[keep], y[keep])
    l1 = l1_line(x, y)
    rob = rpm.lmrob_m("time ~ n_shocks", data=shock, control=cont)

    section("Fitted lines")
    table(
        "intercept, slope",
        {
            "LS (all 16 points)": ls_all,
            "LS (dropping 1, 2, 4)": ls_clean,
            "L1": l1,
            "M (bisquare, eff 0.85)": (
                float(rob.coefficients[0]),
                float(rob.coefficients[1]),
            ),
        },
    )

    # The M-fit lands on the deleted-outlier answer without being told which
    # points to delete. That equivalence is the whole example.
    table(
        "M-fit minus LS-without-outliers",
        {
            "intercept": float(rob.coefficients[0]) - ls_clean[0],
            "slope": float(rob.coefficients[1]) - ls_clean[1],
        },
    )

    table("Robust scale", {"sigma": rob.sigma()})

    section("Which observations did the M-estimator downweight?")
    weights = rob.weights()
    downweighted = weights[weights < 0.5]
    table(
        "robustness weight < 0.5 (1-based index)",
        {str(i + 1): float(w) for i, w in downweighted.items()},
    )

    # Figure 4.3 — every line on one scatter plot.
    rpm.plot.scatter_with_fit(
        rob,
        x="n_shocks",
        show_ols=True,
        title="Shock data — M-estimate vs least squares (Figure 4.3)",
        save=figure("ch04_shock_fits"),
    )


if __name__ == "__main__":
    run(main)
