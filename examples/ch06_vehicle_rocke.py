"""Chapter 6, Example 6.3, the Rocke estimator in higher dimensions (Figure 6.7).

Python port of ``vehicle.R``.

217 vehicle silhouettes measured on 18 variables. At p = 18 the difference
between robust estimators starts to matter: a bisquare S-estimator's efficiency
degrades as dimension grows, which is exactly the problem the Rocke
estimator's ρ function is designed for.

``vehicle.R`` compares four scatter estimates, classical, MCD, bisquare-S and
Rocke, via chi-squared Q-Q plots of the Mahalanobis distances. MCD and
bisquare-S come from ``rrcov``, which this package does not wrap (they are
comparators, not RobStatTM estimators), so the comparison here is classical vs
``covRobMM`` vs ``covRobRocke``.

R packages required: RobStatTM only.
"""
from __future__ import annotations

import numpy as np
from _common import chisq_quantile, figure, run, section, table

import robstattm_py as rpm

LEVEL = 0.999


def main() -> None:
    section("Chapter 6, Example 6.3, vehicle data")

    vehicle = rpm.datasets.vehicle()
    x = vehicle.to_numpy(dtype=float)
    n, p = x.shape
    print(f"  {n} observations in {p} dimensions")

    classical = rpm.cov_classic(x)
    mm = rpm.cov_rob_mm(x)
    rocke = rpm.cov_rob_rocke(x)

    cutoff = chisq_quantile(LEVEL, p)
    section(f"Figure 6.7, distances against the {LEVEL:.1%} chi-squared cutoff")
    print(f"  cutoff (chi-squared, {p} df): {cutoff:.4f}\n")

    counts: dict[str, int] = {}
    for label, result in (
        ("classical", classical),
        ("covRobMM", mm),
        ("covRobRocke (Figure 6.7, right panel)", rocke),
    ):
        distances = np.asarray(result.dist, dtype=float)
        counts[label] = int((distances > cutoff).sum())
        table(
            label,
            {
                "outliers found": counts[label],
                "median distance": float(np.median(distances)),
                "largest distance": float(distances.max()),
            },
        )

    print(
        "\n  The median distance is the diagnostic to read here. For a clean\n"
        f"  sample it should sit near the chi-squared median ({chisq_quantile(0.5, p):.2f}\n"
        "  on 18 df). A classical estimate that has absorbed the outliers pulls\n"
        "  the bulk of the distances down; a robust one does not."
    )

    section("Where do the two robust estimators disagree?")
    mm_dist = np.asarray(mm.dist, dtype=float)
    rocke_dist = np.asarray(rocke.dist, dtype=float)
    mm_flag = set(np.flatnonzero(mm_dist > cutoff) + 1)
    rocke_flag = set(np.flatnonzero(rocke_dist > cutoff) + 1)
    table(
        "flagged observations (1-based)",
        {
            "both": len(mm_flag & rocke_flag),
            "MM only": sorted(int(i) for i in mm_flag - rocke_flag),
            "Rocke only": sorted(int(i) for i in rocke_flag - mm_flag),
        },
    )

    rpm.plot.distance_distance(
        rocke,
        classical,
        title="Vehicle, Rocke vs classical distances (Figure 6.7)",
        save=figure("ch06_vehicle_distance_distance"),
    )


if __name__ == "__main__":
    run(main)
