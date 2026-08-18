"""Chapter 4, Example 4.2, robust ANOVA on the oats data (Figures 4.2, 4.4).

Python port of ``oats.R``.

A two-factor agricultural trial: yield by variety and block. The data set ships
two responses, ``response1`` as recorded, and ``response2``, the same
experiment with a few values altered. Fitting both under classical and robust
ANOVA gives a 2x4 table of p-values, and the interesting cell is the one where
altering a handful of observations flips a classical conclusion while the
robust test holds its ground.

``rob.linear.test`` is the robust analogue of comparing two nested models with
``anova()``: fit the full model and the reduced one, then test the dropped
terms.

Note carried over from ``oats.R``: code changes made after the book went to
press mean not every p-value matches the printed example exactly.

R packages required: RobStatTM only.
"""
from __future__ import annotations

import numpy as np
from _common import figure, require_python_packages, run, section, table

import robstattm_py as rpm


def classical_f_test(
    data, response: str, full_terms: list[str], reduced_terms: list[str]
) -> float:
    """Return the p-value of the classical nested-model F test.

    Stands in for R's ``anova(full, reduced)``. Written out with numpy rather
    than pulled from statsmodels: it is the *non-robust* comparator here, and
    the examples should not take on a dependency for a baseline.
    """
    import pandas as pd
    from scipy import stats

    y = data[response].to_numpy(dtype=float)

    def rss(terms: list[str]) -> tuple[float, int]:
        if terms:
            design = pd.get_dummies(data[terms], drop_first=True, dtype=float)
            matrix = np.column_stack([np.ones(len(y)), design.to_numpy(dtype=float)])
        else:
            matrix = np.ones((len(y), 1))
        coef, *_ = np.linalg.lstsq(matrix, y, rcond=None)
        resid = y - matrix @ coef
        return float(np.sum(resid**2)), matrix.shape[1]

    rss_full, k_full = rss(full_terms)
    rss_red, k_red = rss(reduced_terms)
    df1 = k_full - k_red
    df2 = len(y) - k_full
    f = ((rss_red - rss_full) / df1) / (rss_full / df2)
    return float(stats.f.sf(f, df1, df2))


def main() -> None:
    section("Chapter 4, Example 4.2, oats data, classical vs robust ANOVA")

    # scipy only for the classical F distribution - the robust half of this
    # example needs nothing beyond the package itself.
    require_python_packages("scipy")

    oats = rpm.datasets.oats()
    for column in ("variety", "block"):
        oats[column] = oats[column].astype("category")

    cont = rpm.lmrobm_control(bb=0.5, efficiency=0.85, family="bisquare")

    results: dict[str, tuple[float, float, float, float]] = {}
    for label, response in (("Original", "response1"), ("Altered", "response2")):
        full = rpm.lmrob_m(
            f"{response} ~ variety + block", data=oats, control=cont
        )
        # Dropping `variety` leaves `block`, and vice versa.
        drop_variety = rpm.lmrob_m(f"{response} ~ block", data=oats, control=cont)
        drop_block = rpm.lmrob_m(f"{response} ~ variety", data=oats, control=cont)

        results[label] = (
            classical_f_test(oats, response, ["variety", "block"], ["block"]),
            rpm.rob_linear_test(full, drop_variety).f_pvalue,
            classical_f_test(oats, response, ["variety", "block"], ["variety"]),
            rpm.rob_linear_test(full, drop_block).f_pvalue,
        )

        if response == "response2":
            scale = full.sigma()
            std_resid = full.resid().to_numpy() / scale
            flagged = np.flatnonzero(np.abs(std_resid) > 2.5) + 1
            section("Figure 4.4, standardized robust residuals, altered response")
            table(
                "beyond 2.5 robust scales (1-based)",
                {"observations": list(flagged), "robust scale": scale},
            )
            rpm.plot.qq(
                full,
                title="Oats (altered response), robust residual Q-Q (Figure 4.4)",
                save=figure("ch04_oats_qq"),
            )

    section("p-values of the ANOVA tests")
    print(f"\n  {'':<10}{'F(rows)':>12}{'Robust(rows)':>14}"
          f"{'F(cols)':>12}{'Robust(cols)':>14}")
    for label, row in results.items():
        print(f"  {label:<10}" + "".join(f"{v:>12.4f}  " for v in row))

    print(
        "\n  Read down each pair of columns. Altering a few observations moves the\n"
        "  classical p-values much further than the robust ones, which is the\n"
        "  whole claim being made: the robust test's conclusion is a property of\n"
        "  the experiment, not of its worst few measurements."
    )


if __name__ == "__main__":
    run(main)
