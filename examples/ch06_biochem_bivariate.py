"""Chapter 6, Example 6.1 — one point moves a correlation (Figs 6.1-6.2, Table 6.1).

Python port of ``biochem.R``.

Twelve bivariate observations of phosphate and chloride. Observation 3 is an
outlier, and the example does nothing more than compute the classical mean,
variance and correlation with and without it. The correlation is the number to
watch: one point out of twelve is enough to change it substantially, and
nothing in the classical summary warns you.

This is the simplest possible statement of the problem the rest of Chapter 6
solves, so the robust estimator is shown here too — as a contrast with the
"delete and recompute" approach, which only works when you already know what to
delete.

R packages required: RobStatTM only.
"""
from __future__ import annotations

import numpy as np
from _common import figure, run, section, table

import robstattm_py as rpm

OUTLIER = 3  # 1-based, as the book numbers it


def classical_summary(x: np.ndarray) -> dict[str, float]:
    """Means, variances and the correlation — R's ``colMeans``/``var``/``cor``."""
    cov = np.cov(x, rowvar=False, ddof=1)
    return {
        "mean Phosphate": float(x[:, 0].mean()),
        "mean Chloride": float(x[:, 1].mean()),
        "var Phosphate": float(cov[0, 0]),
        "var Chloride": float(cov[1, 1]),
        "correlation": float(cov[0, 1] / np.sqrt(cov[0, 0] * cov[1, 1])),
    }


def main() -> None:
    section("Chapter 6, Example 6.1 — biochem data")

    biochem = rpm.datasets.biochem()
    biochem.columns = ["Phosphate", "Chloride"]
    x = biochem.to_numpy(dtype=float)

    keep = np.ones(len(x), dtype=bool)
    keep[OUTLIER - 1] = False

    section("Table 6.1 — classical summaries, with and without observation 3")
    table("all 12 observations", classical_summary(x))
    table(f"observation {OUTLIER} deleted", classical_summary(x[keep]))

    all_rho = classical_summary(x)["correlation"]
    cut_rho = classical_summary(x[keep])["correlation"]
    print(
        f"\n  The correlation moves from {all_rho:.4f} to {cut_rho:.4f} when one\n"
        f"  observation out of {len(x)} is removed. Neither figure is marked as\n"
        "  uncertain by anything the classical summary reports."
    )

    section("What a robust estimator says without being told about observation 3")
    rob = rpm.cov_rob_mm(x)
    rob_cov = np.asarray(rob.cov, dtype=float)
    table(
        "covRobMM on all 12 observations",
        {
            "mean Phosphate": float(rob.center[0]),
            "mean Chloride": float(rob.center[1]),
            "var Phosphate": float(rob_cov[0, 0]),
            "var Chloride": float(rob_cov[1, 1]),
            "correlation": float(
                rob_cov[0, 1] / np.sqrt(rob_cov[0, 0] * rob_cov[1, 1])
            ),
        },
    )
    print(
        "\n  Be careful how you read this. The robust correlation moves only part\n"
        "  of the way toward the deleted-observation value — with twelve points in\n"
        "  two dimensions there is not much data left to work with once one is\n"
        "  discounted, and the MM estimator moderates observation 3 rather than\n"
        "  rejecting it. Where the robust fit is unambiguous is in the distances\n"
        "  below: it identifies the point. Identification is the reliable service\n"
        "  a robust estimator provides at this sample size; a fully outlier-free\n"
        "  correlation is not."
    )

    section("Figure 6.1 / 6.2 — which observation is furthest out?")
    distances = np.asarray(rob.dist, dtype=float)
    order = np.argsort(distances)[::-1][:3]
    table(
        "largest robust Mahalanobis distances (1-based index)",
        {str(int(i) + 1): float(distances[i]) for i in order},
    )

    rpm.plot.mahalanobis_panel(
        rob,
        title="Biochem — robust distances (Figures 6.1, 6.2)",
        save=figure("ch06_biochem_distances"),
    )


if __name__ == "__main__":
    run(main)
