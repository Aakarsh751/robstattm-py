"""Vignette — comparing a classical and a robust fit side by side.

Python port of ``fitmodelsRobStatTM.R``.

The R script uses the ``fit.models`` framework, which bundles two fits of the
same data into one object so that ``coef``, ``summary`` and ``plot`` show them
together. There is no ``fit.models`` here, and wrapping it is out of scope for
this package — a separate project, ``fitmodels-py``, does that.

What this package provides instead is direct: fit each model, read the same
accessors off both, and use ``plot.compare_fits`` to draw them on one set of
axes. That covers what the vignette's ``fit.models`` object is used *for*,
without the indirection.

Both halves of the R script are ported: the regression comparison on the
mineral data, and the covariance comparison on the first three wine variables.

R packages required: RobStatTM only.
"""
from __future__ import annotations

import numpy as np
from _common import figure, ols, run, section, table

import robstattm_py as rpm


def main() -> None:
    section("Vignette part 1 — LS against MM on the mineral data")

    mineral = rpm.datasets.mineral()
    copper = mineral["copper"].to_numpy(dtype=float)
    zinc = mineral["zinc"].to_numpy(dtype=float)

    ls_coef = ols(copper, zinc)
    # The vignette's control is "mopt" at 0.95 efficiency, which is also the
    # default — so this is the same fit as lmrobdet_mm("zinc ~ copper", ...).
    control = rpm.lmrobdet_control(family="mopt", efficiency=0.95)
    rob = rpm.lmrobdet_mm("zinc ~ copper", data=mineral, control=control)

    section("coef(fmLSrob) — both fits' coefficients")
    print(f"\n  {'':<14}{'(Intercept)':>14}{'copper':>12}")
    print(f"  {'LS':<14}{ls_coef[0]:>14.3f}{ls_coef[1]:>12.3f}")
    print(
        f"  {'lmrobdetMM':<14}{float(rob.coefficients[0]):>14.3f}"
        f"{float(rob.coefficients[1]):>12.3f}"
    )

    section("summary(fmLSrob) — the robust half")
    print(rob.summary())

    section("The accessors the fit.models object exposes")
    table(
        "lmrobdetMM fit",
        {
            "sigma()": rob.sigma(),
            "R²": float(rob.r_squared),
            "n coefficients": len(rob.coef_names),
            "residuals (first 3)": tuple(rob.resid().to_numpy()[:3]),
            "weights (first 3)": tuple(rob.weights().to_numpy()[:3]),
        },
    )
    print("\n  vcov():")
    print(rob.vcov().to_string(float_format=lambda v: f"{v:.5g}"))

    # plot(fmLSrob) draws both fits together; this is the equivalent.
    rpm.plot.scatter_with_fit(
        rob,
        x="copper",
        show_ols=True,
        title="Mineral — robust and least-squares fits together",
        save=figure("vignette_mineral_compare"),
    )
    rpm.plot.diagnostics(
        rob,
        title="Mineral — lmrobdetMM diagnostics",
        save=figure("vignette_mineral_diagnostics"),
    )

    # -- Part 2 ------------------------------------------------------------
    section("Vignette part 2 — covClassic against covRob on wine[, 1:3]")

    wine3 = rpm.datasets.wine().iloc[:, :3]
    classic = rpm.cov_classic(wine3.to_numpy(dtype=float))
    # type="auto" picks MM or Rocke from the dimension, as the vignette does.
    robust = rpm.cov_rob(wine3.to_numpy(dtype=float), type="auto")

    table(
        "location",
        {
            "classical": tuple(float(v) for v in np.asarray(classic.center)),
            "robust": tuple(float(v) for v in np.asarray(robust.center)),
        },
    )
    table(
        "estimator chosen by type='auto'", {"estimator": robust.estimator_type}
    )

    print("\n  classical covariance:")
    print(np.array2string(np.asarray(classic.cov, dtype=float), precision=4))
    print("\n  robust covariance:")
    print(np.array2string(np.asarray(robust.cov, dtype=float), precision=4))

    rpm.plot.cov_heatmap(
        robust,
        classic,
        title="Wine[, 1:3] — robust vs classical covariance",
        save=figure("vignette_wine3_covariance"),
    )
    rpm.plot.distance_distance(
        robust,
        classic,
        title="Wine[, 1:3] — distance-distance plot",
        save=figure("vignette_wine3_distances"),
    )


if __name__ == "__main__":
    run(main)
