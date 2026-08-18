"""Chapter 7, Example 7.3, robust Poisson regression on the Breslow data.

Python port of ``epilepsy.R`` (Figures 7.6, 7.7, Table 7.3).

59 epilepsy patients, seizure counts before and during treatment with
progabide. Count data with a couple of extreme responses, fitted four ways:

* ML - ``glm(family = poisson)``;
* CUBIF - conditionally unbiased bounded-influence (``robcbi::cubinf``);
* MT and RQL - the two ``robustbase::glmrob`` methods.

``epilepsy.R`` carries two notes worth preserving. First, the MLE values in
Table 7.3 of the book are incorrect, the ones computed here are right. Second,
there is no R implementation of the MP estimator, so the book's MP coefficients
were produced in MATLAB; they are hard-coded in the R script and reproduced
here as constants rather than recomputed.

R packages required: RobStatTM, plus ``robustbase`` and ``robcbi`` (which needs
``robeth``).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from _common import figure, require_r_packages, run, section, table

import robstattm_py as rpm

TERMS = ("intercept", "Age10", "Base4", "Progabide", "Base4:Progabide")

#: Book's MP coefficients, computed in MATLAB - see the module docstring.
MP_COEFFICIENTS = np.array([2.0078, 0.0707, 0.1346, -0.4898, 0.0476])


def build_design(breslow: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """Recreate ``epilepsy.R``'s design: the same columns, by position."""
    y = breslow.iloc[:, 9].to_numpy(dtype=float)          # seizure count
    age10 = breslow.iloc[:, 10].to_numpy(dtype=float)
    base4 = breslow.iloc[:, 11].to_numpy(dtype=float)
    progabide = (breslow.iloc[:, 7] == "progabide").to_numpy(dtype=float)

    data = pd.DataFrame(
        {
            "y": y,
            "Age10": age10,
            "Base4": base4,
            "Progabide": progabide,
            "interaction": base4 * progabide,
        }
    )
    return data, y


def main() -> None:
    section("Chapter 7, Example 7.3, Breslow epilepsy data")

    require_r_packages("robustbase", "robcbi")

    breslow = rpm.datasets.breslow_dat()
    data, y = build_design(breslow)
    print(f"  {len(y)} patients; seizure counts {y.min():.0f} to {y.max():.0f}")

    formula = "y ~ Age10 + Base4 + Progabide + interaction"
    rql = rpm.glmrob(formula, data=data, family="poisson")
    mt = rpm.glmrob(formula, data=data, family="poisson", method="MT")

    design = np.column_stack(
        [
            np.ones(len(y)),
            data["Age10"],
            data["Base4"],
            data["Progabide"],
            data["interaction"],
        ]
    )
    cubif = rpm.cubinf(design, y, family="poisson", null_dev=False, ufact=1.1)
    ml_coef = _ml_poisson(design, y)

    section("Table 7.3, coefficients")
    print(f"\n  {'estimator':<12}" + "".join(f"{t:>18}" for t in TERMS))
    for label, coef in (
        ("ML", ml_coef),
        ("CUBIF", np.asarray(cubif.coefficients, dtype=float)),
        ("MT", np.asarray(mt.coefficients, dtype=float)),
        ("RQL", np.asarray(rql.coefficients, dtype=float)),
        ("MP (MATLAB)", MP_COEFFICIENTS),
    ):
        print(f"  {label:<12}" + "".join(f"{float(c):>18.4f}" for c in coef))

    section("Figures 7.6 / 7.7, absolute deviance residuals")
    deviances = {
        "ML": np.abs(_poisson_deviance_residuals(y, np.exp(design @ ml_coef))),
        "CUBIF": np.abs(
            _poisson_deviance_residuals(y, np.asarray(cubif.fitted_values, dtype=float))
        ),
        "MT": np.abs(
            _poisson_deviance_residuals(
                y, np.exp(design @ np.asarray(mt.coefficients, dtype=float))
            )
        ),
        "RQL": np.abs(
            _poisson_deviance_residuals(
                y, np.exp(design @ np.asarray(rql.coefficients, dtype=float))
            )
        ),
        "MP": np.abs(_poisson_deviance_residuals(y, np.exp(design @ MP_COEFFICIENTS))),
    }
    print(f"\n  {'estimator':<12}{'median':>12}{'upper quartile':>17}{'max':>12}")
    for label, dev in deviances.items():
        print(
            f"  {label:<12}{np.median(dev):>12.4f}"
            f"{np.quantile(dev, 0.75):>17.4f}{dev.max():>12.4f}"
        )

    print(
        "\n  This is Figure 7.6's boxplot as a table. The robust estimators give\n"
        "  the *smaller* median and quartile, they describe the bulk better,\n"
        "  while their maxima are larger, because the two extreme patients are\n"
        "  left standing out rather than fitted."
    )

    section("Figure 7.7, the 48 smallest residuals, MT against ML")
    mt_sorted = np.sort(deviances["MT"])[:48]
    ml_sorted = np.sort(deviances["ML"])[:48]
    table(
        "sum over the 48 non-extreme patients",
        {"MT": float(mt_sorted.sum()), "ML": float(ml_sorted.sum())},
    )

    rpm.plot.location_scale(
        rpm.loc_scale_m(deviances["MT"]),
        deviances["MT"],
        title="Epilepsy, MT absolute deviance residuals (Figure 7.6)",
        save=figure("ch07_epilepsy_deviances"),
    )


def _ml_poisson(design: np.ndarray, y: np.ndarray, *, tol: float = 1e-12) -> np.ndarray:
    """Maximum-likelihood Poisson regression by IRLS, R's ``glm(poisson)``."""
    beta = np.zeros(design.shape[1])
    beta[0] = np.log(max(y.mean(), 1e-6))
    for _ in range(200):
        mu = np.clip(np.exp(design @ beta), 1e-10, None)
        z = design @ beta + (y - mu) / mu
        root_w = np.sqrt(mu)
        step = np.linalg.lstsq(design * root_w[:, None], z * root_w, rcond=None)[0]
        converged = np.max(np.abs(step - beta)) < tol
        beta = step
        if converged:
            break
    return beta


def _poisson_deviance_residuals(y: np.ndarray, mu: np.ndarray) -> np.ndarray:
    """Signed Poisson deviance residuals, as ``epilepsy.R`` computes them."""
    mu = np.clip(np.asarray(mu, dtype=float).ravel(), 1e-10, None)
    safe_y = np.maximum(y, 1.0)
    deviance = 2.0 * (y * np.log(safe_y) - y - y * np.log(mu) + mu)
    return np.sign(y - mu) * np.sqrt(np.maximum(deviance, 0.0))


if __name__ == "__main__":
    run(main)
