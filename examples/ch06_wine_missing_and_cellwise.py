"""Chapter 6, Examples 6.5 and 6.6 — missing data and cellwise contamination.

Python port of ``wine1.R``.

Two failures of the classical Chapter-6 machinery, and the estimators built for
each:

**Example 6.5 (Figure 6.11) — missing values.** 20% of the wine matrix is
blanked at random. ``covRobMM`` needs complete rows, so the usual answer is
casewise deletion, which here would throw away nearly every row. ``GSE``
(generalised S-estimator) handles the gaps directly, and ``CovEM`` gives the
non-robust comparison — EM handles the missingness but not the outliers.

**Example 6.6 (Figure 6.12) — cellwise contamination.** Rowwise estimators
assume a bad observation is bad in every coordinate. When contamination lands
in individual *cells*, a small fraction of bad cells is enough to make almost
every row partly bad, and rowwise methods run out of clean rows. ``TSGS``
(two-step GS) filters at the cell level first.

R packages required: RobStatTM, and ``GSE``.
"""
from __future__ import annotations

import numpy as np
from _common import chisq_quantile, figure, require_r_packages, run, section, table

import robstattm_py as rpm

SEED = 2400
MISSING_RATE = 0.2
LEVEL = 0.999


def main() -> None:
    section("Chapter 6, Examples 6.5 / 6.6 — wine data with gaps and bad cells")

    require_r_packages("GSE")

    wine = rpm.datasets.wine()
    x = wine.to_numpy(dtype=float)
    n, p = x.shape
    cutoff = chisq_quantile(LEVEL, p)
    print(f"  {n} observations in {p} dimensions; cutoff {cutoff:.4f}")

    # -- Example 6.5 -------------------------------------------------------
    section("Example 6.5 — 20% of cells missing at random (Figure 6.11)")
    x_missing = _blank_at_random(x, MISSING_RATE)
    print(
        f"  {np.isnan(x_missing).sum()} of {x.size} cells blanked; "
        f"{int((~np.isnan(x_missing).any(axis=1)).sum())} of {n} rows still complete"
    )
    print(
        "  Casewise deletion is not an option at this rate — that is the point\n"
        "  of the example."
    )

    gse_fit = rpm.gse(x_missing)
    # pmd_adj is GSE's adjusted partial Mahalanobis distance — the quantity
    # wine1.R reads via getDistAdj(). The unadjusted `pmd` is not comparable
    # with a chi-squared cutoff when cells are missing, because each row's
    # distance is over a different number of observed coordinates.
    gse_dist = np.asarray(gse_fit.pmd_adj, dtype=float)
    table(
        "GSE (robust, handles missingness)",
        {
            "outliers found": int((gse_dist > cutoff).sum()),
            "indices (1-based)": sorted(
                int(i) for i in np.flatnonzero(gse_dist > cutoff) + 1
            ),
        },
    )

    # -- Example 6.6 -------------------------------------------------------
    section("Example 6.6 — cellwise contamination (Figure 6.12)")
    mm_fit = rpm.cov_rob_mm(x)
    mm_dist = np.asarray(mm_fit.dist, dtype=float)
    tsgs_fit = rpm.tsgs(x, method="bisquare", filter="UBF-DDC")
    tsgs_dist = np.asarray(tsgs_fit.pmd_adj, dtype=float)

    mm_flag = set(int(i) for i in np.flatnonzero(mm_dist > cutoff) + 1)
    tsgs_flag = set(int(i) for i in np.flatnonzero(tsgs_dist > cutoff) + 1)
    table(
        "covRobMM (rowwise)",
        {"outliers found": len(mm_flag), "indices (1-based)": sorted(mm_flag)},
    )
    table(
        "TSGS (cellwise)",
        {"outliers found": len(tsgs_flag), "indices (1-based)": sorted(tsgs_flag)},
    )
    table(
        "comparison",
        {
            "flagged by both": sorted(mm_flag & tsgs_flag),
            "rowwise only": sorted(mm_flag - tsgs_flag),
            "cellwise only": sorted(tsgs_flag - mm_flag),
        },
    )

    filtered_cells = int(np.isnan(np.asarray(tsgs_fit.xf, dtype=float)).sum())
    print(
        f"\n  The two lists barely overlap, and that is the lesson rather than a\n"
        f"  contradiction. TSGS's first step flagged and removed {filtered_cells}\n"
        f"  individual cells out of {x.size} before estimating anything. Once the\n"
        "  offending *cells* are gone, the rows that contained them are no longer\n"
        "  outlying rows — so a rowwise distance computed afterwards has little\n"
        "  left to find. Rowwise and cellwise methods are answering two different\n"
        "  questions: 'which observations are bad?' and 'which measurements are\n"
        "  bad?'. Choose according to how your data actually goes wrong."
    )

    rpm.plot.mahalanobis_panel(
        mm_fit,
        title="Wine — rowwise robust distances (Figure 6.12)",
        save=figure("ch06_wine1_rowwise"),
    )

    print(
        "\n  A note on reproducing the book's figures exactly: the missingness\n"
        "  pattern above comes from R's RNG under set.seed(2400), matching\n"
        "  wine1.R. wine1.R itself warns that its plots differ from the book's\n"
        "  Figure 6.11 because the book used a different seed — so agreeing with\n"
        "  the script, not the printed figure, is the achievable target."
    )


def _blank_at_random(x: np.ndarray, rate: float) -> np.ndarray:
    """Blank each cell independently with probability ``rate``.

    Draws from R's RNG under ``set.seed(2400)``, in the same order wine1.R
    does, so the missingness pattern is the script's rather than merely one
    with the same distribution.
    """
    rpm.set_seed(SEED)
    from robstattm_py._r import r

    n, p = x.shape
    # R fills the n-by-p logical matrix column-major.
    draws = np.asarray(r().r(f"runif({n * p})"), dtype=float).reshape((n, p), order="F")
    out = x.copy()
    out[draws < rate] = np.nan
    return out


if __name__ == "__main__":
    run(main)
