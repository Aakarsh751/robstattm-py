"""Vignette: comparing a classical and a robust fit side by side.

Python port of ``fitmodelsRobStatTM.R``.

The R script uses the ``fit.models`` framework, which bundles two fits of the
same data into one object so ``coef``, ``summary`` and ``plot`` show them
together. RobStatTM-Py exposes exactly that through :func:`robstattm_py.compare`,
which delegates to the sibling package ``fitmodels-py``. This is the "easily see
if lmrobdetMM produces a different result than lm" comparison the book uses.

Both halves of the R script are ported: the regression comparison on the mineral
data (an ``lmfm``), and the covariance comparison on the first three wine
variables (a ``covfm``).

R packages required: RobStatTM only. Python: ``fitmodels-py`` for ``compare()``
(``pip install robstattm-py[compare]``); the script skips cleanly without it.
"""
from __future__ import annotations

from _common import figure, require_python_packages, run, section, table

import robstattm_py as rpm


def main() -> None:
    # compare() delegates to fitmodels-py; announce and skip if it is absent
    # rather than tracebacking half-way through.
    require_python_packages("fitmodels_py")

    section("Part 1: LS against MM on the mineral data (an lmfm)")

    mineral = rpm.datasets.mineral()
    ls = rpm.lm("zinc ~ copper", data=mineral)
    rob = rpm.lmrobdet_mm("zinc ~ copper", data=mineral)

    fm = rpm.compare(LS=ls, Robust=rob)

    section("coef(fm): both fits' coefficients")
    print(fm.coef().to_string(float_format=lambda v: f"{v:.4f}"))

    section("summary(fm): the coefficient tables lined up")
    print(fm.summary())

    # Each member's own R-style summary is still available directly.
    section("summary.lm on the classical fit alone")
    print(ls.summary())

    rpm.plot.scatter_with_fit(
        rob,
        x="copper",
        show_ols=True,
        title="Mineral: robust and least-squares fits together",
        save=figure("vignette_mineral_compare"),
    )

    # -- Part 2 ------------------------------------------------------------
    section("Part 2: covClassic against covRob on wine[, 1:3] (a covfm)")

    wine3 = rpm.datasets.wine().iloc[:, :3]
    classic = rpm.cov_classic(wine3)
    robust = rpm.cov_rob(wine3, type="auto")

    cov_fm = rpm.compare(Classical=classic, Robust=robust)

    section("summary(covfm): covariance/correlation estimates side by side")
    print(cov_fm.summary())

    section("center(covfm): location estimates, one row per model")
    print(cov_fm.center().to_string(float_format=lambda v: f"{v:.4f}"))

    table(
        "estimator chosen by type='auto'", {"estimator": robust.estimator_type}
    )

    rpm.plot.cov_heatmap(
        robust,
        classic,
        title="Wine[, 1:3]: robust vs classical covariance",
        save=figure("vignette_wine3_covariance"),
    )
    rpm.plot.distance_distance(
        robust,
        classic,
        title="Wine[, 1:3]: distance-distance plot",
        save=figure("vignette_wine3_distances"),
    )


if __name__ == "__main__":
    run(main)
