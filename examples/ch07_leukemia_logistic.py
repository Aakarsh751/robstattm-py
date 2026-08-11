"""Chapter 7, Example 7.1 — robust logistic regression on leukaemia survival.

Python port of ``leukemia.R`` (Figure 7.4, Table 7.1).

33 leukaemia patients; the response is survival past a threshold, the
predictors are white blood cell count and the AG factor. One patient's white
cell count is far above the rest, and in a logistic regression a single
extreme covariate value has a large effect on the maximum-likelihood fit —
there is no residual to be large, so nothing in the standard output flags it.

Four estimators are compared:

* ML — the standard ``glm(family = binomial)`` baseline;
* ``logregWML`` — weighted ML, downweighting high-leverage covariates;
* ``logregBY``  — the Bianco-Yohai estimator;
* ``logregWBY`` — weighted Bianco-Yohai, the one the book recommends.

Figure 7.4 plots the sorted absolute deviance residuals of WBY against ML.

R packages required: RobStatTM only. (``leuk.dat`` ships with RobStatTM.)
"""
from __future__ import annotations

import numpy as np
from _common import (
    figure,
    ml_deviance_residuals,
    ml_logistic,
    run,
    section,
    table,
)

import robstattm_py as rpm


def main() -> None:
    section("Chapter 7, Example 7.1 — leukaemia data")

    leuk = rpm.datasets.leuk_dat()
    x = leuk[["wbc", "ag"]].to_numpy(dtype=float)
    y = leuk["y"].to_numpy(dtype=float)
    print(f"  {len(y)} patients, {int(y.sum())} events")
    print(
        f"  white cell count ranges {x[:, 0].min():.0f} to {x[:, 0].max():.0f} — "
        f"a factor of {x[:, 0].max() / max(x[:, 0].min(), 1):.0f}"
    )

    fits = {
        "WML (weighted ML)": rpm.wml_logreg(x, y),
        "BY": rpm.by_logreg(x, y),
        "WBY (weighted BY)": rpm.wby_logreg(x, y),
    }
    ml_coef = ml_logistic(x, y)

    section("Table 7.1 — coefficients")
    names = ("(Intercept)", "wbc", "ag")
    print(f"\n  {'estimator':<20}" + "".join(f"{n:>14}" for n in names))
    print(f"  {'ML':<20}" + "".join(f"{c:>14.5f}" for c in ml_coef))
    for label, fit in fits.items():
        print(
            f"  {label:<20}"
            + "".join(f"{float(c):>14.5f}" for c in np.asarray(fit.coefficients))
        )

    print(
        "\n  The robust estimators pull the wbc coefficient away from the ML\n"
        "  value. ML is not wrong arithmetically — it is the right answer to a\n"
        "  question that assumed no observation was atypical."
    )

    section("Figure 7.4 — sorted absolute deviance residuals")
    wby = fits["WBY (weighted BY)"]
    wby_dev = np.sort(np.abs(np.asarray(wby.residual_deviances, dtype=float)))
    ml_dev = np.sort(np.abs(ml_deviance_residuals(x, y, ml_coef)))
    print(f"\n  {'quantile':<12}{'WBY':>12}{'ML':>12}")
    for q in (0.5, 0.75, 0.9, 0.95, 1.0):
        i = min(int(q * len(y)), len(y) - 1)
        print(f"  {q:<12.2f}{wby_dev[i]:>12.4f}{ml_dev[i]:>12.4f}")

    table(
        "largest absolute deviance residual",
        {"WBY": float(wby_dev[-1]), "ML": float(ml_dev[-1])},
    )
    print(
        "\n  The robust fit's largest residual is the larger of the two, and that\n"
        "  is the desired outcome: the atypical patient stays visible instead of\n"
        "  being absorbed into the fit."
    )

    section("Convergence")
    for label, fit in fits.items():
        table(label, {"converged": fit.converged, "objective": fit.objective})

    rpm.plot.location_scale(
        rpm.loc_scale_m(np.abs(np.asarray(wby.residual_deviances, dtype=float))),
        np.abs(np.asarray(wby.residual_deviances, dtype=float)),
        title="Leukaemia — WBY absolute deviance residuals",
        save=figure("ch07_leukemia_deviances"),
    )


if __name__ == "__main__":
    run(main)
