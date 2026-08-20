"""MM-regression from robustbase: R's ``robustbase::lmrob``.

The sibling MM-estimator to RobStatTM's ``lmrobdetMM`` (Doug Martin's
``summary.lmrob`` list entry). Wrapping it lets a Python user compare the two MM
implementations directly -- same class of estimator, different defaults and
initial-estimator machinery.

.. note::
   ``lmrob`` uses a random-resampling S-estimator for its initial fit by
   default, so it is **stochastic**. Call :func:`robstattm_py.set_seed` first for
   a reproducible result.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from robstattm_py._converters import extract_array, extract_float
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
class LmrobResult:
    """Result of :func:`lmrob`, mirroring R's ``lmrob`` fit.

    Attributes
    ----------
    coefficients, coef_names, residuals, fitted_values, rank, df_residual, formula
        As for :class:`~robstattm_py.LmResult`.
    scale : float or None
        The robust residual scale.
    converged : bool or None
        Whether the IRWLS converged.
    rweights : numpy.ndarray or None
        Final robustness weights.
    """

    coefficients: np.ndarray
    coef_names: tuple[str, ...]
    residuals: np.ndarray
    fitted_values: np.ndarray
    rank: int
    df_residual: int
    formula: str
    scale: float | None
    converged: bool | None
    rweights: np.ndarray | None
    _r_fit: Any = field(default=None, repr=False, compare=False)
    _data: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        cf = ", ".join(
            f"{n}={v:.4g}"
            for n, v in zip(self.coef_names, self.coefficients, strict=False)
        )
        return f"<LmrobResult: {self.formula} | {cf} | scale={self.scale:.4g}>"

    def coef(self) -> pd.Series:
        """Coefficients as a named pandas Series."""
        return pd.Series(self.coefficients, index=list(self.coef_names), name="coef")

    def summary(self) -> ComparisonSummary:
        """Port of R's ``summary.lmrob`` (coefficient t-table, R-squared)."""
        return summarize(
            self.formula, self._data, model="lmrob",
            call_head="robustbase::lmrob", require="robustbase",
        )

    def predict(
        self, newdata: pd.DataFrame | None = None, *, se_fit: bool = False
    ) -> np.ndarray | ComparisonPrediction:
        """Port of R's ``predict.lmrob``."""
        return predict_classical(
            self.formula, self._data, call_head="robustbase::lmrob",
            require="robustbase", newdata=newdata, se_fit=se_fit,
        )

    def vcov(self) -> pd.DataFrame:
        """Coefficient covariance matrix (R's ``vcov.lmrob``)."""
        return vcov_of(
            self.formula, self._data, call_head="robustbase::lmrob",
            require="robustbase",
        )

    def confint(self, *, level: float = 0.95) -> pd.DataFrame:
        """Wald confidence intervals for the coefficients (``confint``)."""
        return confint_of(
            self.formula, self._data, call_head="robustbase::lmrob",
            require="robustbase", level=level,
        )


def lmrob(
    formula: str | None = None,
    data: pd.DataFrame | None = None,
    *,
    X=None,
    y=None,
) -> LmrobResult:
    """MM-regression via ``robustbase::lmrob``.

    Parameters
    ----------
    formula : str
    data : pandas.DataFrame
    X, y : array-like, optional
        Array invocation (mutually exclusive with formula/data).

    Returns
    -------
    LmrobResult

    Notes
    -----
    Stochastic: seed with :func:`robstattm_py.set_seed` for reproducibility.
    """
    raw = fit_raw(formula, data, pkg_name="robustbase", fn_attr="lmrob", X=X, y=y)
    r_fit = raw["r_fit"]
    sc = rx2_opt(r_fit, "scale")
    conv = rx2_opt(r_fit, "converged")
    rw = rx2_opt(r_fit, "rweights")
    return LmrobResult(
        coefficients=raw["coefficients"],
        coef_names=raw["coef_names"],
        residuals=raw["residuals"],
        fitted_values=raw["fitted_values"],
        rank=raw["rank"],
        df_residual=raw["df_residual"],
        formula=raw["formula"],
        scale=extract_float(sc) if sc is not None else None,
        converged=bool(conv[0]) if conv is not None and len(conv) else None,
        rweights=extract_array(rw).astype(float).ravel() if rw is not None else None,
        _r_fit=r_fit,
        _data=raw["data"],
    )
