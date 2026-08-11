"""Chapter 6, Example 6.7 — robust variance components on the autism data.

Python port of ``autism.R`` (Tables 6.8, 6.9).

41 children measured at five ages, modelling VSAE score against age, age² and
socialisation group. The interest is in the *variance components* — how much
variation belongs to the intercept, the linear age term and the quadratic term,
and how they covary — not just the fixed effects.

Two estimators from ``robustvarComp``: composite-tau, and a classical S fit with
Rocke's psi for comparison.

The data live in the ``WWGbook`` package. The subsetting below reproduces
``autism.R``'s exactly, including the recoding of ``sicdegp`` into ``sicdegp2``
that makes group 3 the reference level.

R packages required: RobStatTM, ``robustvarComp``, ``nlme`` and ``WWGbook``.
"""
from __future__ import annotations

import numpy as np
from _common import require_r_packages, run, section, table

import robstattm_py as rpm

N_TIMES = 5
N_CHILDREN = 41


def main() -> None:
    section("Chapter 6, Example 6.7 — autism data, robust variance components")

    require_r_packages("robustvarComp", "nlme", "WWGbook")

    data = _prepare()
    print(f"  {N_CHILDREN} children with all {N_TIMES} measurements = {len(data)} rows")

    # Ages at the five measurement occasions, centred at 2 as autism.R does.
    z1 = np.ones(N_TIMES)
    z2 = np.array([0.0, 1.0, 3.0, 7.0, 11.0])
    z3 = z2**2
    varcov = [
        np.outer(z1, z1),
        np.outer(z2, z2),
        np.outer(z3, z3),
        np.outer(z1, z2) + np.outer(z2, z1),
        np.outer(z1, z3) + np.outer(z3, z1),
        np.outer(z3, z2) + np.outer(z2, z3),
    ]
    names = ("Int", "age", "age2", "Int:age", "Int:age2", "age:age2")

    # Column 1 indexes the occasion, column 2 the child — the layout
    # varComprob expects, and the order autism.R builds it in.
    groups = np.column_stack(
        [
            np.repeat(np.arange(1, N_TIMES + 1), N_CHILDREN),
            np.tile(np.arange(1, N_CHILDREN + 1), N_TIMES),
        ]
    )

    formula = (
        "vsae ~ age_2 + I(age_2^2) + sicdegp2_f "
        "+ age_2:sicdegp2_f + I(age_2^2):sicdegp2_f"
    )
    # The variance components are non-negative; the fixed effects are not.
    lower = [0.01, 0.01, 0.01, -np.inf, -np.inf, -np.inf]

    section("Table 6.8 — composite tau")
    tau = rpm.var_comprob(
        formula,
        data,
        groups=groups,
        varcov=varcov,
        varcov_names=names,
        control=rpm.var_comprob_control(lower=lower),
    )
    _report(tau, names)

    section("Table 6.9 — classical S with Rocke psi")
    s_fit = rpm.var_comprob(
        formula,
        data,
        groups=groups,
        varcov=varcov,
        varcov_names=names,
        control=rpm.var_comprob_control(
            method="S", psi="rocke", cov_init="covOGK", lower=lower
        ),
    )
    _report(s_fit, names)


def _report(fit, names: tuple[str, ...]) -> None:
    table(
        "fixed effects",
        {
            str(n): float(v)
            for n, v in zip(
                fit.beta_names, np.asarray(fit.beta, dtype=float), strict=False
            )
        },
    )
    table(
        "variance components (eta)",
        {
            str(n): float(v)
            for n, v in zip(
                fit.eta_names or names,
                np.asarray(fit.eta, dtype=float).ravel(),
                strict=False,
            )
        },
    )
    table(
        "gamma (eta rescaled by the residual scale)",
        {
            str(n): float(v)
            for n, v in zip(
                names, np.asarray(fit.gamma, dtype=float).ravel(), strict=False
            )
        },
    )
    table(
        "fit",
        {"method": fit.method, "objective": float(fit.min), "iterations": fit.iterations},
    )


def _prepare():
    """Reproduce ``autism.R``'s data preparation.

    Kept close to the R, because the subset is not incidental: dropping to the
    41 children with a complete set of five measurements is what makes the
    balanced ``groups``/``varcov`` structure below valid.
    """
    autism = rpm.datasets.load("WWGbook", "autism").dropna()

    complete = autism["childid"].value_counts()
    keep_ids = complete[complete == N_TIMES].index
    autism = autism[autism["childid"].isin(keep_ids)].copy()

    autism["age_2"] = autism["age"] - 2
    # Recode so group 3 becomes the reference (0), as autism.R does. The levels
    # are stringified because rpy2 can only build an R factor from string
    # categories — an integer-valued category silently falls back to a
    # character column, which changes the contrasts R fits.
    recode = {3: "0", 2: "2", 1: "1"}
    autism["sicdegp2_f"] = autism["sicdegp"].map(recode).astype("category")
    return autism.reset_index(drop=True)


if __name__ == "__main__":
    run(main)
