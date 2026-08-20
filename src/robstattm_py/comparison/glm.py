"""Classical generalised linear models: R's ``stats::glm``.

The classical baseline for RobStatTM-Py's robust GLMs (the robust logistic
regressions ``by_logreg`` / ``wby_logreg`` / ``wml_logreg`` and the external
``glmrob``). Fit a classical ``glm`` on the same data to see what robustness
changed. Defaults to ``family="binomial"`` because logistic regression is the
comparison this wrapper exists for; pass another R family name for others.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from robstattm_py._converters import extract_float
from robstattm_py._r import r, rx2_opt
from robstattm_py.comparison._common import (
    ComparisonPrediction,
    ComparisonSummary,
    confint_of,
    fit_raw,
    predict_classical,
    summarize,
    vcov_of,
)


@dataclass(frozen=True, slots=True)
class GlmResult:
    """Result of :func:`glm`, mirroring R's ``glm`` fit.

    Attributes
    ----------
    coefficients, coef_names, residuals, fitted_values, rank, df_residual, formula
        As for :class:`~robstattm_py.LmResult`.
    family : str
        The R family used (e.g. ``"binomial"``).
    deviance, null_deviance, aic : float or None
        Model fit statistics from the R fit.
    """

    coefficients: np.ndarray
    coef_names: tuple[str, ...]
    residuals: np.ndarray
    fitted_values: np.ndarray
    rank: int
    df_residual: int
    formula: str
    family: str
    deviance: float | None
    null_deviance: float | None
    aic: float | None
    _r_fit: Any = field(default=None, repr=False, compare=False)
    _data: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        cf = ", ".join(
            f"{n}={v:.4g}"
            for n, v in zip(self.coef_names, self.coefficients, strict=False)
        )
        return f"<GlmResult({self.family}): {self.formula} | {cf}>"

    def coef(self) -> pd.Series:
        """Coefficients as a named pandas Series."""
        return pd.Series(self.coefficients, index=list(self.coef_names), name="coef")

    def summary(self) -> ComparisonSummary:
        """Port of R's ``summary.glm`` (coefficient z/t-table, dispersion)."""
        return summarize(
            self.formula, self._data, model="glm", call_head="glm",
            extra=f", family = {self.family}",
        )

    def predict(
        self,
        newdata: pd.DataFrame | None = None,
        *,
        se_fit: bool = False,
        type: str = "link",
    ) -> np.ndarray | ComparisonPrediction:
        """Port of R's ``predict.glm``.

        ``type`` is R's ``predict.glm`` type: ``"link"`` (default, linear
        predictor scale) or ``"response"`` (probability scale for binomial).
        """
        if type not in ("link", "response", "terms"):
            raise ValueError("type must be 'link', 'response' or 'terms'")
        return predict_classical(
            self.formula, self._data, call_head="glm",
            extra=f", family = {self.family}",
            newdata=newdata, se_fit=se_fit, predict_args=f", type = '{type}'",
        )

    def vcov(self) -> pd.DataFrame:
        """Coefficient covariance matrix (R's ``vcov.glm``)."""
        return vcov_of(
            self.formula, self._data, call_head="glm",
            extra=f", family = {self.family}",
        )

    def confint(self, *, level: float = 0.95) -> pd.DataFrame:
        """Profile-likelihood confidence intervals (R's ``confint.glm``)."""
        return confint_of(
            self.formula, self._data, call_head="glm",
            extra=f", family = {self.family}", level=level,
        )


def glm(
    formula: str | None = None,
    data: pd.DataFrame | None = None,
    *,
    family: str = "binomial",
    X=None,
    y=None,
) -> GlmResult:
    """Classical generalised linear model via ``stats::glm``.

    Parameters
    ----------
    formula : str
        R-style formula, e.g. ``"y ~ x1 + x2"``.
    data : pandas.DataFrame
    family : str, default "binomial"
        R family name: ``"binomial"``, ``"poisson"``, ``"Gamma"``,
        ``"gaussian"``, ... The default is logistic regression, the comparison
        for the robust logistic wrappers.
    X, y : array-like, optional
        Array invocation (mutually exclusive with formula/data).

    Returns
    -------
    GlmResult
    """
    ro = r()
    fam_obj = ro.r(family)  # the family generator function; glm() calls it
    raw = fit_raw(
        formula, data, pkg_name="stats", fn_attr="glm", X=X, y=y,
        extra_named={"family": fam_obj},
    )
    r_fit = raw["r_fit"]

    def _opt(name):
        v = rx2_opt(r_fit, name)
        return extract_float(v) if v is not None else None

    return GlmResult(
        coefficients=raw["coefficients"],
        coef_names=raw["coef_names"],
        residuals=raw["residuals"],
        fitted_values=raw["fitted_values"],
        rank=raw["rank"],
        df_residual=raw["df_residual"],
        formula=raw["formula"],
        family=family,
        deviance=_opt("deviance"),
        null_deviance=_opt("null.deviance"),
        aic=_opt("aic"),
        _r_fit=r_fit,
        _data=raw["data"],
    )
