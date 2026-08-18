"""Chapter 6, Example 6.2, masking in the wine data (Figure 6.3).

Python port of ``wine.R``. The flagship multivariate example.

59 Italian wines measured on 13 variables. Classical Mahalanobis distances find
essentially nothing: the outliers are numerous enough to inflate the sample
covariance, and an inflated covariance is exactly what makes a large distance
look ordinary. This is *masking*, and it gets worse with dimension, which is why
13 variables is enough to hide what 2 variables could not.

Robust distances, from ``covRobMM`` and from the Rocke S-estimator, are
computed against a scatter matrix the outliers did not get to influence, so the
same points stand out clearly.

R packages required: RobStatTM only.
"""
from __future__ import annotations

import numpy as np
from _common import chisq_quantile, figure, run, section, table

import robstattm_py as rpm

#: chi-squared cutoff used throughout Chapter 6.
LEVEL = 0.999


def main() -> None:
    section("Chapter 6, Example 6.2, wine data")

    wine = rpm.datasets.wine()
    x = wine.to_numpy(dtype=float)
    n, p = x.shape
    print(f"  {n} observations in {p} dimensions")

    classical = rpm.cov_classic(x)
    mm = rpm.cov_rob_mm(x)
    rocke = rpm.cov_rob_rocke(x)

    cutoff = chisq_quantile(LEVEL, p)
    section(f"Figure 6.3, points beyond the {LEVEL:.1%} chi-squared cutoff")
    print(f"  cutoff (chi-squared, {p} df): {cutoff:.4f}")

    flags: dict[str, list[int]] = {}
    for label, result in (
        ("classical", classical),
        ("covRobMM", mm),
        ("covRobRocke", rocke),
    ):
        distances = np.asarray(result.dist, dtype=float)
        flagged = sorted(np.flatnonzero(distances > cutoff) + 1)
        flags[label] = [int(i) for i in flagged]
        table(
            label,
            {
                "outliers found": len(flagged),
                "indices (1-based)": flags[label],
                "largest distance": float(distances.max()),
            },
        )

    print(
        f"\n  Classical distances flag {len(flags['classical'])} points; the robust\n"
        f"  estimators flag {len(flags['covRobMM'])} and {len(flags['covRobRocke'])}.\n"
        "  The data did not change between those three rows, only whether the\n"
        "  yardstick was allowed to be set by the points being measured."
    )

    section("Do the two robust estimators agree?")
    both = sorted(set(flags["covRobMM"]) & set(flags["covRobRocke"]))
    table(
        "agreement",
        {
            "flagged by both": both,
            "MM only": sorted(set(flags["covRobMM"]) - set(flags["covRobRocke"])),
            "Rocke only": sorted(set(flags["covRobRocke"]) - set(flags["covRobMM"])),
        },
    )

    rpm.plot.distance_distance(
        mm,
        classical,
        title="Wine, robust vs classical distances (Figure 6.3)",
        save=figure("ch06_wine_distance_distance"),
    )
    rpm.plot.mahalanobis_panel(
        mm,
        title="Wine, robust Mahalanobis distances (Figure 6.3)",
        save=figure("ch06_wine_distances"),
    )


if __name__ == "__main__":
    run(main)
