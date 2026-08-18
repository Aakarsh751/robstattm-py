"""Chapter 2, Table 2.4, robust location on the flour data.

Python port of ``flour.R`` from RobStatTM's ``inst/scripts/``.

Compares three estimates of location on 24 flour aphlatoxin measurements: the
sample mean, an M-estimator (``locScaleM``), and a 25% trimmed mean, each with
its standard error and 95% confidence interval.

The point of the example is the width and position of the third column. One
contaminated observation is enough to drag the mean, and the mean's own
standard error does not warn you about it; the M-estimator and the trimmed mean
both stay with the bulk of the data.

A note on which psi function: ``flour.R`` calls ``locScaleM(x, eff = 0.95)``
and then labels the result "bisquare M-estimator", but ``locScaleM``'s default
psi is ``"mopt"``, not bisquare, the label predates the change of default. Both
are printed below so the numbers can be matched against either the script's
actual output or the book's Table 2.4.

R packages required: RobStatTM only.
"""
from __future__ import annotations

import numpy as np
from _common import figure, run, section, table

import robstattm_py as rpm


def trimmed_mean(x: np.ndarray, alpha: float) -> tuple[float, float]:
    """Return the ``alpha``-trimmed mean and its standard error.

    Direct transcription of the ``trimean`` helper defined inside ``flour.R``.
    It is written out in the R script rather than taken from a package, so it
    is written out here too, the variance formula below is the one the book
    uses, not ``scipy.stats.trim_mean``'s.
    """
    n = len(x)
    m = int(np.floor(n * alpha))
    xs = np.sort(x)
    core = xs[m : n - m]
    mu = core.mean()
    centred = xs - mu
    a = m * centred[m - 1] ** 2 + m * centred[n - m] ** 2 + np.sum((core - mu) ** 2)
    mu_std = np.sqrt((a / (n - 2 * m)) / n)
    return float(mu), float(mu_std)


def main() -> None:
    section("Chapter 2, flour data: mean vs M-estimator vs trimmed mean")

    flour = rpm.datasets.flour()
    x = flour.iloc[:, 0].to_numpy(dtype=float)
    n = len(x)
    # 0.975 normal quantile, hard-coded so the example needs no scipy.
    qn = 1.959963984540054

    # Sample mean.
    xbar = float(x.mean())
    se_mean = float(x.std(ddof=1) / np.sqrt(n))

    # M-estimator of location and scale, exactly as flour.R calls it: default
    # psi, which is "mopt".
    res = rpm.loc_scale_m(x, eff=0.95)
    mu_m, se_m = float(res.mu), float(res.std_mu)

    # The same estimator under bisquare, which is what the script's own comment
    # and the book's table label refer to.
    res_bi = rpm.loc_scale_m(x, psi="bisquare", eff=0.95)
    mu_bi, se_bi = float(res_bi.mu), float(res_bi.std_mu)

    # 25% trimmed mean.
    mu_25, se_25 = trimmed_mean(x, 0.25)

    section("Table 2.4")
    table(
        "Location estimates",
        {
            "mean": xbar,
            "M (mopt)": mu_m,
            "M (bisquare)": mu_bi,
            "25% trimmed": mu_25,
        },
    )
    table(
        "Estimated standard deviations",
        {
            "mean": se_mean,
            "M (mopt)": se_m,
            "M (bisquare)": se_bi,
            "25% trimmed": se_25,
        },
    )
    table(
        "0.95 confidence intervals",
        {
            "mean": (xbar - qn * se_mean, xbar + qn * se_mean),
            "M (mopt)": (mu_m - qn * se_m, mu_m + qn * se_m),
            "M (bisquare)": (mu_bi - qn * se_bi, mu_bi + qn * se_bi),
            "25% trimmed": (mu_25 - qn * se_25, mu_25 + qn * se_25),
        },
    )

    # The M-estimator also reports a robust scale, which the R script does not
    # print but which is what makes its standard error trustworthy here. Compare
    # it with the sample SD: the mean's interval is eight times wider.
    table(
        "Dispersion",
        {"robust scale (mopt)": float(res.disper), "sample SD": float(x.std(ddof=1))},
    )

    # A picture of why: the M-estimate sits on the mode, the mean does not.
    rpm.plot.location_scale(res, x, title="Flour data, robust vs classical location",
                            save=figure("ch02_flour_location"))


if __name__ == "__main__":
    run(main)
