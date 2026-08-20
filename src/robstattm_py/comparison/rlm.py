"""Huber-type M-estimator regression: R's ``MASS::rlm``.

The textbook robust-regression baseline. Comparing it against RobStatTM's
``lmrobM`` / ``lmrobdetMM`` shows how a modern MM-estimator differs from the
classic monotone-M approach. Deterministic given its default psi.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from robstattm_py._converters import extract_float
from robstattm_py._r import rx2_opt
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
class RlmResult:
    """Result of :func:`rlm`, mirroring R's ``rlm`` fit.

    Attributes
    ----------
    coefficients, coef_names, residuals, fitted_values, rank, df_residual, formula
        As for :class:`~robstattm_py.LmResult`.
    scale : float or None
        The robust residual scale ``s`` used in the IRLS.
    """

    coefficients: np.ndarray
    coef_names: tuple[str, ...]
    residuals: np.ndarray
    fitted_values: np.ndarray
    rank: int
    df_residual: int
    formula: str
    scale: float | None
    _r_fit: Any = field(default=None, repr=False, compare=False)
    _data: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        cf = ", ".join(
            f"{n}={v:.4g}"
            for n, v in zip(self.coef_names, self.coefficients, strict=False)
        )
        return f"<RlmResult: {self.formula} | {cf} | s={self.scale:.4g}>"

    def coef(self) -> pd.Series:
        """Coefficients as a named pandas Series."""
        return pd.Series(self.coefficients, index=list(self.coef_names), name="coef")

    def summary(self) -> ComparisonSummary:
        """Port of R's ``summary.rlm`` (coefficient table; no p-values)."""
        return summarize(
            self.formula, self._data, model="rlm",
            call_head="MASS::rlm", require="MASS",
        )

    def predict(
        self, newdata: pd.DataFrame | None = None, *, se_fit: bool = False
    ) -> np.ndarray | ComparisonPrediction:
        """Port of R's ``predict.rlm``."""
        return predict_classical(
            self.formula, self._data, call_head="MASS::rlm", require="MASS",
            newdata=newdata, se_fit=se_fit,
        )

    def vcov(self) -> pd.DataFrame:
        """Coefficient covariance matrix (R's ``vcov`` on the rlm fit)."""
        return vcov_of(
            self.formula, self._data, call_head="MASS::rlm", require="MASS",
        )

    def confint(self, *, level: float = 0.95) -> pd.DataFrame:
        """Wald confidence intervals for the coefficients (``confint.default``)."""
        return confint_of(
            self.formula, self._data, call_head="MASS::rlm", require="MASS",
            level=level,
        )


def rlm(
    formula: str | None = None,
    data: pd.DataFrame | None = None,
    *,
    X=None,
    y=None,
) -> RlmResult:
    """Huber-type robust M-regression via ``MASS::rlm``.

    Parameters
    ----------
    formula : str
    data : pandas.DataFrame
    X, y : array-like, optional
        Array invocation (mutually exclusive with formula/data).

    Returns
    -------
    RlmResult
    """
    raw = fit_raw(formula, data, pkg_name="MASS", fn_attr="rlm", X=X, y=y)
    r_fit = raw["r_fit"]
    s = rx2_opt(r_fit, "s")
    return RlmResult(
        coefficients=raw["coefficients"],
        coef_names=raw["coef_names"],
        residuals=raw["residuals"],
        fitted_values=raw["fitted_values"],
        rank=raw["rank"],
        df_residual=raw["df_residual"],
        formula=raw["formula"],
        scale=extract_float(s) if s is not None else None,
        _r_fit=r_fit,
        _data=raw["data"],
    )
