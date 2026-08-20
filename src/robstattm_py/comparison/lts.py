"""Least Trimmed Squares regression: R's ``robustbase::ltsReg``.

The high-breakdown LTS estimator behind Doug Martin's ``summary.lts`` list entry.
A useful robust alternative to line up against RobStatTM's MM estimators: LTS and
MM reach robustness by different routes, so comparing them is informative.

.. note::
   ``ltsReg`` is **stochastic** (it subsamples elemental subsets). Call
   :func:`robstattm_py.set_seed` first for a reproducible fit.
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
class LtsResult:
    """Result of :func:`lts_reg`, mirroring R's ``ltsReg`` fit.

    Attributes
    ----------
    coefficients, coef_names, residuals, fitted_values, rank, df_residual, formula
        As for :class:`~robstattm_py.LmResult`.
    scale : float or None
        The final LTS scale estimate.
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
        return f"<LtsResult: {self.formula} | {cf} | scale={self.scale:.4g}>"

    def coef(self) -> pd.Series:
        """Coefficients as a named pandas Series."""
        return pd.Series(self.coefficients, index=list(self.coef_names), name="coef")

    def summary(self) -> ComparisonSummary:
        """Port of R's ``summary.lts`` (coefficient t-table, R-squared)."""
        return summarize(
            self.formula, self._data, model="ltsReg",
            call_head="robustbase::ltsReg", require="robustbase",
        )

    def predict(
        self, newdata: pd.DataFrame | None = None, *, se_fit: bool = False
    ) -> np.ndarray | ComparisonPrediction:
        """Port of R's ``predict.lts``."""
        return predict_classical(
            self.formula, self._data, call_head="robustbase::ltsReg",
            require="robustbase", newdata=newdata, se_fit=se_fit,
        )

    def vcov(self) -> pd.DataFrame:
        """Coefficient covariance matrix (R's ``vcov`` on the ltsReg fit)."""
        return vcov_of(
            self.formula, self._data, call_head="robustbase::ltsReg",
            require="robustbase",
        )

    def confint(self, *, level: float = 0.95) -> pd.DataFrame:
        """Wald confidence intervals for the coefficients (``confint.default``)."""
        return confint_of(
            self.formula, self._data, call_head="robustbase::ltsReg",
            require="robustbase", level=level,
        )


def lts_reg(
    formula: str | None = None,
    data: pd.DataFrame | None = None,
    *,
    X=None,
    y=None,
) -> LtsResult:
    """Least Trimmed Squares regression via ``robustbase::ltsReg``.

    Parameters
    ----------
    formula : str
    data : pandas.DataFrame
    X, y : array-like, optional
        Array invocation (mutually exclusive with formula/data).

    Returns
    -------
    LtsResult

    Notes
    -----
    Stochastic: seed with :func:`robstattm_py.set_seed` for reproducibility.
    """
    raw = fit_raw(formula, data, pkg_name="robustbase", fn_attr="ltsReg", X=X, y=y)
    r_fit = raw["r_fit"]
    sc = rx2_opt(r_fit, "scale")
    return LtsResult(
        coefficients=raw["coefficients"],
        coef_names=raw["coef_names"],
        residuals=raw["residuals"],
        fitted_values=raw["fitted_values"],
        rank=raw["rank"],
        df_residual=raw["df_residual"],
        formula=raw["formula"],
        scale=extract_float(sc) if sc is not None else None,
        _r_fit=r_fit,
        _data=raw["data"],
    )
