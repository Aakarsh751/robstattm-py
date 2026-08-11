"""Vignette — a tour of the package.

Python port of ``VignetteRobStatTM.R``, which is the RobStatTM package
vignette: where the data live, how to fit the main estimators, and what you get
back.

The R vignette is a knitr document whose chunks mostly write PNG files. What is
reproduced here is its *content* — the same datasets, the same fits, the same
comparisons — in the order it presents them, with the numbers printed rather
than plotted.

Anything in the R vignette that is about R itself (``install.packages``,
``help()``, ``system.file("scripts", ...)``) has a Python counterpart shown
below instead of being dropped.

R packages required: RobStatTM, plus ``robustbase`` for the ``wood`` data.
"""
from __future__ import annotations

import numpy as np
from _common import figure, l1_line, ols, require_r_dataset, run, section, table

import robstattm_py as rpm


def main() -> None:
    section("Where things live")
    print(f"  robstattm_py version: {rpm.__version__}")
    print(f"  built-in datasets:    {len(rpm.datasets.available())}")
    print("  example scripts:      this directory\n")
    print("  R's `system.file('scripts', package='RobStatTM')` lists the R")
    print("  scripts these examples are ported from.")

    section("Datasets — head(shock, 2) and head(wood, 1)")
    shock = rpm.datasets.shock()
    print("\n  shock:")
    print(shock.head(2).to_string())

    require_r_dataset("robustbase", "wood")
    wood = rpm.datasets.load("robustbase", "wood")
    print("\n  wood (from robustbase):")
    print(wood.head(1).to_string())

    print(f"\n  datasets.info('mineral'): {rpm.datasets.info('mineral')}")

    section("Regression — LS, L1 and MM on the mineral data")
    mineral = rpm.datasets.mineral()
    copper = mineral["copper"].to_numpy(dtype=float)
    zinc = mineral["zinc"].to_numpy(dtype=float)

    control = rpm.lmrobdet_control(family="mopt", efficiency=0.95)
    rob = rpm.lmrobdet_mm("zinc ~ copper", data=mineral, control=control)

    print(f"\n  {'':<14}{'(Intercept)':>14}{'copper':>12}")
    for label, coef in (
        ("lm (LS)", ols(copper, zinc)),
        ("rq (L1)", l1_line(copper, zinc)),
        ("lmrobdetMM", tuple(float(c) for c in rob.coefficients)),
    ):
        print(f"  {label:<14}{coef[0]:>14.4f}{coef[1]:>12.4f}")

    section("summary(fmLSrob)")
    print(rob.summary())

    section("Result methods — what an lmrobdetMM fit gives you")
    table(
        "accessors",
        {
            "coef()": tuple(float(v) for v in rob.coef()),
            "sigma()": rob.sigma(),
            "resid() length": len(rob.resid()),
            "fitted() length": len(rob.fitted()),
            "weights() min": float(rob.weights().min()),
            "hatvalues() max": float(rob.hatvalues().max()),
        },
    )
    print("\n  predict() on two new copper values:")
    import pandas as pd

    newdata = pd.DataFrame({"copper": [10.0, 500.0]})
    print(f"    {np.asarray(rob.predict(newdata)).round(4)}")

    section("Covariance — covClassic against covRob on wine[, 1:5]")
    wine5 = rpm.datasets.wine().iloc[:, :5].to_numpy(dtype=float)
    classic = rpm.cov_classic(wine5)
    robust = rpm.cov_rob(wine5, type="auto")

    table(
        "eigenvalues of the covariance matrix",
        {
            "classical": tuple(
                float(v) for v in np.linalg.eigvalsh(np.asarray(classic.cov))[::-1]
            ),
            "robust": tuple(
                float(v) for v in np.linalg.eigvalsh(np.asarray(robust.cov))[::-1]
            ),
        },
    )
    print(
        "\n  This is the vignette's 'eigenvalues' plot as numbers. The leading\n"
        "  classical eigenvalue is inflated by the outliers — which is the same\n"
        "  thing that masks them in the distance plot below."
    )

    classic_dist = np.asarray(classic.dist, dtype=float)
    robust_dist = np.asarray(robust.dist, dtype=float)
    table(
        "Mahalanobis distances",
        {
            "classical max": float(classic_dist.max()),
            "robust max": float(robust_dist.max()),
            "ratio": float(robust_dist.max() / classic_dist.max()),
        },
    )

    section("Robust PCA on the same five variables")
    pca = rpm.prcomp_rob(wine5)
    table(
        "prcompRob",
        {
            "components": len(np.asarray(pca.sdev, dtype=float)),
            "sdev": tuple(float(v) for v in np.asarray(pca.sdev, dtype=float)),
        },
    )

    section("Where to read more")
    print("  rpm.help('lmrobdet_mm')  — the R man page for any wrapper")
    print("  rpm.list_names()         — every wrapper and its R name")
    print("  rpm.check_setup()        — verify R and each R package")
    print("  https://aakarsh751.github.io/robstattm-py/")

    rpm.plot.distance_distance(
        robust,
        classic,
        title="Wine[, 1:5] — distance-distance (vignette)",
        save=figure("vignette_tour_distances"),
    )
    rpm.plot.scree(pca, title="Wine[, 1:5] — robust PCA scree (vignette)",
                   save=figure("vignette_tour_scree"))


if __name__ == "__main__":
    run(main)
