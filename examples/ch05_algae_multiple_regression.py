"""Chapter 5, Example 5.4, multiple regression on the algae data (Figs 5.14-5.15).

Python port of ``algae.R``.

90 river samples, 11 predictors, response ``V12``. Unlike the mineral example
there is no single obvious outlier to point at; the contamination only becomes
visible in the residual Q-Q plot, and only once the fit itself has stopped being
dragged by it. That is the point of comparing Figure 5.14 (least-squares
residuals, outliers partly absorbed into the fit) with Figure 5.15 (robust
residuals, outliers stand clear at 2.5 robust scales).

Uses a dot formula, ``V12 ~ .``, which R expands against the data frame; the
factor columns expand further into level indicators, so there are more
coefficients than columns.

R packages required: RobStatTM only.
"""
from __future__ import annotations

import numpy as np
from _common import figure, run, section, table

import robstattm_py as rpm


def main() -> None:
    section("Chapter 5, Example 5.4, algae data")

    algae = rpm.datasets.algae()
    print(f"  {algae.shape[0]} observations, {algae.shape[1] - 1} predictors")

    # The book's control (bisquare, 85%). algae.R notes that the current
    # defaults (mopt, 95%) barely change Figure 5.15.
    cont = rpm.lmrobdet_control(bb=0.5, efficiency=0.85, family="bisquare")
    rob = rpm.lmrobdet_mm("V12 ~ .", data=algae, control=cont)

    # Least squares on the same model. V1-V3 are categorical, so they have to
    # be expanded the way R's model.matrix does - one indicator per level after
    # the first - or the two fits would not be comparable.
    y = algae["V12"].to_numpy(dtype=float)
    ls_resid, ls_sigma = _least_squares(algae, y)

    section("Fit summary")
    print(rob.summary())

    section("Scale comparison")
    table(
        "residual scale",
        {"least squares": ls_sigma, "MM (bisquare, 0.85)": rob.sigma()},
    )
    print(
        "\n  Note these are not the same quantity and the robust one is not\n"
        "  automatically smaller: the least-squares figure is the usual RSS/df,\n"
        "  minimised by construction, while the robust figure is an M-scale of\n"
        "  residuals from a fit that declined to chase the outliers. What the\n"
        "  robust scale buys is not a smaller number but a *stable* one, it is\n"
        "  the yardstick the flags below are measured against."
    )

    section("Figures 5.14 / 5.15, residuals beyond 2.5 scales")
    rob_resid = rob.resid().to_numpy()
    ls_flagged = np.flatnonzero(np.abs(ls_resid) > 2.5 * ls_sigma) + 1
    rob_flagged = np.flatnonzero(np.abs(rob_resid) > 2.5 * rob.sigma()) + 1
    table(
        "observations flagged (1-based)",
        {
            "least squares": list(ls_flagged),
            "MM": list(rob_flagged),
        },
    )
    print(
        "\n  algae.R singles out observations 36 and 77. Least squares hides\n"
        "  some of what the robust fit exposes, because they helped determine\n"
        "  the least-squares line in the first place."
    )

    rpm.plot.qq(
        rob,
        title="Algae, robust residual Q-Q (Figure 5.15)",
        save=figure("ch05_algae_qq_robust"),
    )
    rpm.plot.diagnostics(
        rob,
        title="Algae, MM diagnostics",
        save=figure("ch05_algae_diagnostics"),
    )


def _least_squares(data, y: np.ndarray) -> tuple[np.ndarray, float]:
    """Return ``(residuals, residual scale)`` for ``lm(V12 ~ .)``.

    ``drop_first=True`` reproduces R's default treatment contrasts, so this
    design matrix has the same 16 columns as the robust fit's, check
    ``fit.coef_names`` if you want to confirm the correspondence.
    """
    import pandas as pd

    predictors = data.drop(columns=["V12"])
    design = pd.get_dummies(predictors, drop_first=True, dtype=float)
    design.insert(0, "(Intercept)", 1.0)
    matrix = design.to_numpy(dtype=float)

    coef, *_ = np.linalg.lstsq(matrix, y, rcond=None)
    resid = y - matrix @ coef
    dof = len(y) - matrix.shape[1]
    return resid, float(np.sqrt(np.sum(resid**2) / dof))


if __name__ == "__main__":
    run(main)
