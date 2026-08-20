"""Classical least-squares regression: R's ``stats::lm``.

This is the reference model for the robust regressions in RobStatTM-Py. As Doug
Martin put it, "one needs the lm summary method to easily see if lmrobdetMM
produces a different result than lm" -- so this wrapper exists to be lined up
against :func:`robstattm_py.lmrobdet_mm` and friends.

It is a native Python wrapper (not R's ``lm`` object handed through rpy2): the
result is a frozen dataclass whose fields are numpy/pandas, and ``.summary()``
ports ``summary.lm`` into the same style as the robust-regression summaries.
Numbers match R field-by-field.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

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
class LmResult:
    """Result of :func:`lm`, mirroring R's ``lm`` fit.

    Attributes
    ----------
    coefficients : numpy.ndarray, shape (p,)
    coef_names : tuple[str, ...]
    residuals : numpy.ndarray, shape (n,)
    fitted_values : numpy.ndarray, shape (n,)
    rank : int
    df_residual : int
    formula : str
    """

    coefficients: np.ndarray
    coef_names: tuple[str, ...]
    residuals: np.ndarray
    fitted_values: np.ndarray
    rank: int
    df_residual: int
    formula: str
    _r_fit: Any = field(default=None, repr=False, compare=False)
    _data: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        cf = ", ".join(
            f"{n}={v:.4g}"
            for n, v in zip(self.coef_names, self.coefficients, strict=False)
        )
        return f"<LmResult: {self.formula} | {cf} | df.resid={self.df_residual}>"

    def coef(self) -> pd.Series:
        """Coefficients as a named pandas Series."""
        return pd.Series(self.coefficients, index=list(self.coef_names), name="coef")

    def summary(self) -> ComparisonSummary:
        """Port of R's ``summary.lm`` (coefficient t-table, sigma, R^2, F)."""
        return summarize(self.formula, self._data, model="lm", call_head="lm")

    def predict(
        self, newdata: pd.DataFrame | None = None, *, se_fit: bool = False
    ) -> np.ndarray | ComparisonPrediction:
        """Port of R's ``predict.lm``."""
        return predict_classical(
            self.formula, self._data, call_head="lm", newdata=newdata, se_fit=se_fit
        )

    def vcov(self) -> pd.DataFrame:
        """Coefficient covariance matrix (R's ``vcov.lm``)."""
        return vcov_of(self.formula, self._data, call_head="lm")

    def confint(self, *, level: float = 0.95) -> pd.DataFrame:
        """Confidence intervals for the coefficients (R's ``confint.lm``)."""
        return confint_of(self.formula, self._data, call_head="lm", level=level)


def lm(
    formula: str | None = None,
    data: pd.DataFrame | None = None,
    *,
    X=None,
    y=None,
) -> LmResult:
    """Classical least-squares linear regression via ``stats::lm``.

    The reference model for RobStatTM-Py's robust regressions. Fit it on the
    same data as :func:`robstattm_py.lmrobdet_mm` and compare ``.summary()``
    tables, or line both up with :func:`robstattm_py.compare` for R's
    ``fit.models`` side-by-side view.

    Parameters
    ----------
    formula : str
        R-style formula, e.g. ``"zinc ~ copper"``.
    data : pandas.DataFrame
        Data referenced by ``formula``.
    X, y : array-like, optional
        Alternative array invocation (mutually exclusive with formula/data).

    Returns
    -------
    LmResult

    Examples
    --------
    >>> import robstattm_py as rpm
    >>> df = rpm.datasets.mineral()
    >>> fit = rpm.lm("zinc ~ copper", data=df)
    >>> fit.coef().round(3)          # doctest: +SKIP
    (Intercept)    2.702
    copper         0.135
    Name: coef, dtype: float64
    """
    raw = fit_raw(formula, data, pkg_name="stats", fn_attr="lm", X=X, y=y)
    return LmResult(
        coefficients=raw["coefficients"],
        coef_names=raw["coef_names"],
        residuals=raw["residuals"],
        fitted_values=raw["fitted_values"],
        rank=raw["rank"],
        df_residual=raw["df_residual"],
        formula=raw["formula"],
        _r_fit=raw["r_fit"],
        _data=raw["data"],
    )
