"""Chapter 5, Example 5.1 — MM-regression on the mineral data (Figures 5.1-5.7).

Python port of ``mineral.R``. This is the book's flagship regression example.

53 paired measurements of zinc and copper content. Observation 15 is a single
high-leverage outlier, and it is enough to reverse the apparent relationship:
the least-squares line through all 53 points slopes the wrong way compared with
the line through the other 52.

The script fits four things and compares them:

* least squares on all the data,
* least squares with observation 15 deleted,
* an L1 fit (``quantreg::rq`` in R; see the note in ``ch04_shock_lmrobm.py``),
* MM-regression (``lmrobdetMM``), which recovers the deleted-outlier answer
  without being told that observation 15 is special.

``mineral.R`` uses ``family = "bisquare"`` with ``efficiency = 0.85``. Its own
comments recommend the current defaults (``"mopt"``, ``efficiency = 0.95``)
instead, so both are fitted here and the difference is printed.

R packages required: RobStatTM only.
"""
from __future__ import annotations

import numpy as np
from _common import figure, l1_line, ols, run, section, table

import robstattm_py as rpm

#: 1-based index of the outlier, as the book numbers it.
OUTLIER = 15


def main() -> None:
    section("Chapter 5, Example 5.1 — mineral data")

    mineral = rpm.datasets.mineral()
    copper = mineral["copper"].to_numpy(dtype=float)
    zinc = mineral["zinc"].to_numpy(dtype=float)

    keep = np.ones(len(zinc), dtype=bool)
    keep[OUTLIER - 1] = False

    ls_all = ols(copper, zinc)
    ls_drop = ols(copper[keep], zinc[keep])
    l1 = l1_line(copper, zinc)

    # The book's control.
    book = rpm.lmrobdet_control(bb=0.5, efficiency=0.85, family="bisquare")
    mm_book = rpm.lmrobdet_mm("zinc ~ copper", data=mineral, control=book)
    # Today's recommended defaults.
    mm_now = rpm.lmrobdet_mm("zinc ~ copper", data=mineral)

    section("Figure 5.1 / 5.4 — the fitted lines")
    table(
        "intercept, slope",
        {
            "LS (all 53)": ls_all,
            f"LS (dropping {OUTLIER})": ls_drop,
            "L1": l1,
            "MM (bisquare, 0.85)": tuple(float(c) for c in mm_book.coefficients),
            "MM (mopt, 0.95)": tuple(float(c) for c in mm_now.coefficients),
        },
    )
    print(
        f"\n  The LS slope is {ls_all[1]:+.4f}; dropping one point out of 53 moves it\n"
        f"  to {ls_drop[1]:+.4f}. Both MM fits land near the latter without being told\n"
        f"  which point to drop."
    )

    section("Table 5.1 — coefficient table for the MM fit")
    print(mm_book.summary())

    section("Robust scale and R²")
    table(
        "MM (bisquare, 0.85)",
        {"scale": mm_book.sigma(), "R²": float(mm_book.r_squared)},
    )
    table(
        "MM (mopt, 0.95)",
        {"scale": mm_now.sigma(), "R²": float(mm_now.r_squared)},
    )

    section(f"Figure 5.5 — is observation {OUTLIER} downweighted?")
    weights = mm_book.weights()
    table(
        "robustness weight < 0.5 (1-based index)",
        {str(i + 1): float(w) for i, w in weights[weights < 0.5].items()},
    )

    # Figures 5.1 and 5.4: scatter with the robust and least-squares lines.
    rpm.plot.scatter_with_fit(
        mm_book,
        x="copper",
        show_ols=True,
        title="Mineral data — MM vs least squares (Figures 5.1, 5.4)",
        save=figure("ch05_mineral_scatter"),
    )
    # Figures 5.2, 5.3, 5.6: residual diagnostics for the robust fit.
    rpm.plot.diagnostics(
        mm_book,
        title="Mineral data — MM diagnostics (Figures 5.2, 5.3, 5.6)",
        save=figure("ch05_mineral_diagnostics"),
    )

    # Figure 5.7: sorted |LS residual| against sorted |robust residual|, with
    # the outlier removed from both so the axes are readable.
    ls_resid = np.abs(zinc - (ls_all[0] + ls_all[1] * copper))
    mm_resid = np.abs(mm_book.resid().to_numpy())
    section("Figure 5.7 — sorted absolute residuals, LS vs robust")
    table(
        "largest 5 (outlier excluded)",
        {
            "LS": tuple(np.sort(ls_resid)[:-1][-5:]),
            "MM": tuple(np.sort(mm_resid)[:-1][-5:]),
        },
    )


if __name__ == "__main__":
    run(main)
