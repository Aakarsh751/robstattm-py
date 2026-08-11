"""Chapter 5, Example 5.2 — high-leverage outliers in the wood data (Figs 5.8-5.12).

Python port of ``wood.R``.

The modified wood-specific-gravity data from ``robustbase``: 20 observations,
5 predictors, of which four (4, 6, 8 and 19) were altered to create
*high-leverage* outliers. Leverage is what makes this case harder than the
mineral data — the bad points sit far out in predictor space, so least squares
can pass close to them while missing the other sixteen, and its residuals give
almost no warning.

The comparison to watch is Figure 5.9 (least-squares Q-Q, nothing much to see)
against Figure 5.11 (robust Q-Q, four points clearly outside 2.5 scales).

R packages required: RobStatTM, and ``robustbase`` for the ``wood`` data.
"""
from __future__ import annotations

import numpy as np
from _common import figure, require_r_dataset, run, section, table

import robstattm_py as rpm

#: 1-based indices the book identifies as the altered observations.
ALTERED = (4, 6, 8, 19)


def main() -> None:
    section("Chapter 5, Example 5.2 — wood data")

    # `wood` lives in robustbase, not RobStatTM — guard the dataset, not just
    # the package, because a package can be installed without its data.
    require_r_dataset("robustbase", "wood")
    wood = rpm.datasets.load("robustbase", "wood")
    print(f"  {wood.shape[0]} observations, {wood.shape[1] - 1} predictors")

    cont = rpm.lmrobdet_control(bb=0.5, efficiency=0.85, family="bisquare")
    mm = rpm.lmrobdet_mm("y ~ .", data=wood, control=cont)

    y = wood["y"].to_numpy(dtype=float)
    design = np.column_stack(
        [np.ones(len(y)), wood.drop(columns=["y"]).to_numpy(dtype=float)]
    )
    ls_coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    ls_resid = y - design @ ls_coef
    ls_sigma = float(np.sqrt(np.sum(ls_resid**2) / (len(y) - design.shape[1])))

    section("Fit summary")
    print(mm.summary())

    section("Figures 5.9 / 5.11 — what each fit's residuals reveal")
    mm_resid = mm.resid().to_numpy()
    ls_flagged = sorted(np.flatnonzero(np.abs(ls_resid) > 2.5 * ls_sigma) + 1)
    mm_flagged = sorted(np.flatnonzero(np.abs(mm_resid) > 2.5 * mm.sigma()) + 1)
    table(
        "observations beyond 2.5 residual scales (1-based)",
        {
            "least squares": ls_flagged,
            "MM": mm_flagged,
            "altered in the book": list(ALTERED),
        },
    )
    found = set(mm_flagged) & set(ALTERED)
    print(
        f"\n  The MM fit recovers {len(found)} of the {len(ALTERED)} altered "
        f"observations;\n  least squares flags {len(ls_flagged)}. High leverage is "
        "precisely the case\n  where a least-squares residual is least informative — "
        "the fit bends\n  toward the bad point, so the residual it leaves behind is "
        "small."
    )

    section("Figure 5.10 — leverage")
    hat = mm.hatvalues()
    order = np.argsort(hat)[::-1][: len(ALTERED)]
    table(
        "highest leverage (1-based index -> hat value)",
        {str(int(i) + 1): float(hat[i]) for i in order},
    )
    table(
        "leverage of the altered observations",
        {str(i): float(hat[i - 1]) for i in ALTERED},
    )
    print(
        "\n  Worth noticing: these are *classical* hat values, computed from the\n"
        "  design matrix alone, and they do not single the altered points out.\n"
        "  Leverage says where a point sits in predictor space, not whether it\n"
        "  is wrong — which is why the robust residuals above, and not this\n"
        "  table, are what identifies them."
    )

    section("Figure 5.12 — sorted |residual|, LS vs MM, outliers removed")
    drop = np.abs(mm_resid) > 2.5 * mm.sigma()
    table(
        "largest 5 of the retained points",
        {
            "LS": tuple(np.sort(np.abs(ls_resid[~drop]))[-5:]),
            "MM": tuple(np.sort(np.abs(mm_resid[~drop]))[-5:]),
        },
        fmt="{:.5f}",
    )

    rpm.plot.qq(mm, title="Wood — robust residual Q-Q (Figure 5.11)",
                save=figure("ch05_wood_qq_robust"))
    rpm.plot.resid_vs_leverage(mm, title="Wood — residual vs leverage (Figure 5.10)",
                               save=figure("ch05_wood_leverage"))


if __name__ == "__main__":
    run(main)
