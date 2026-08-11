"""Result-object ergonomics — promised by ``docs/user_interface.md §6 & §10``.

Every wrapper returns a frozen ``@dataclass`` (call it ``X``). For uniform
UX we want every such ``X`` to support::

    X.to_dict()         # plain-Python dict, suitable for JSON / inspection
    X.to_r()            # original rpy2 R object (for round-trip work in R)
    X._repr_html_()     # rich Jupyter rendering
    X.coef_df()         # regression-only, pandas Series

Instead of editing 17 dataclass files, we install the methods once at
import time. Frozen + slotted dataclasses still allow new methods on the
class object — only ``__slots__`` blocks new *data* fields.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any

import numpy as np
import pandas as pd

# ---------- public free functions ----------------------------------------

def _result_to_dict(self: Any) -> dict[str, Any]:
    """Return a plain-Python ``dict`` view of ``self``.

    - Skips fields whose name starts with ``_`` (private state, R handles).
    - Leaves NumPy arrays as-is (callers can ``.tolist()`` if they need
      JSON-clean output).
    - Recurses into nested result dataclasses.
    """
    out: dict[str, Any] = {}
    for f in fields(self):
        if f.name.startswith("_"):
            continue
        v = getattr(self, f.name)
        if is_dataclass(v) and hasattr(v, "to_dict"):
            out[f.name] = v.to_dict()
        else:
            out[f.name] = v
    return out


def _result_to_r(self: Any) -> Any:
    """Return the underlying rpy2 R object.

    Convenient for round-tripping back into R for downstream analysis::

        fit_r = fit.to_r()
        r('predict')(fit_r, newdata = ...)
    """
    if not hasattr(self, "_r_fit") or self._r_fit is None:
        raise RuntimeError(
            f"{type(self).__name__}._r_fit is unavailable (was the object "
            "unpickled? The raw R handle is not pickled — see decisions.md "
            "D-007 on pickle safety)."
        )
    return self._r_fit


def _result_repr_html(self: Any) -> str:
    """Generic HTML rendering for any result dataclass.

    Builds a small HTML table from the public scalar/array-summary fields.
    Result classes that want a richer view should override ``_repr_html_``
    in their own class body (e.g. ``LmrobdetMMSummary`` already does).
    """
    rows: list[str] = []
    for f in fields(self):
        if f.name.startswith("_"):
            continue
        v = getattr(self, f.name)
        rendered = _render_value_html(v)
        if rendered is None:
            continue
        rows.append(
            f"<tr><th style='text-align:left'>{f.name}</th>"
            f"<td>{rendered}</td></tr>"
        )
    title = type(self).__name__
    return (
        f"<div><b>{title}</b></div>"
        f"<table class='dataframe'>{''.join(rows)}</table>"
    )


def _render_value_html(v: Any) -> str | None:
    """Render one field value to HTML. Returns ``None`` to skip."""
    if v is None:
        return "<i>None</i>"
    if isinstance(v, bool):
        return repr(v)
    if isinstance(v, (int, float, np.floating, np.integer)):
        if isinstance(v, float) or isinstance(v, np.floating):
            return f"{float(v):.5g}"
        return str(int(v))
    if isinstance(v, str):
        return f"<code>{v}</code>"
    if isinstance(v, np.ndarray):
        if v.ndim == 0:
            return f"{float(v):.5g}"
        if v.ndim == 1 and v.size <= 6:
            return "[" + ", ".join(f"{float(x):.4g}" for x in v) + "]"
        return f"<i>ndarray, shape={v.shape}</i>"
    if isinstance(v, pd.DataFrame):
        return v.to_html(float_format="%.5g")
    if isinstance(v, (list, tuple)):
        if len(v) <= 6:
            return repr(v)
        return f"<i>{type(v).__name__}, len={len(v)}</i>"
    return None  # skip unknown types from the table


# ---------- regression-specific helper -----------------------------------

# Plotting shortcuts delegate to the native suite ``robstattm_py.plot`` (D-023).
# Default backend is native matplotlib (returns an Axes/Figure, per
# docs/user_interface.md §6); pass ``backend="r"`` for the Path-A PNG.

def _plot_residuals(self: Any, **kw):
    """Residuals-vs-fitted plot (R's ``plot(fit, which = 1)``). Returns an Axes."""
    from robstattm_py import plot
    return plot.residuals(self, **kw)


def _plot_qq(self: Any, **kw):
    """Normal Q-Q plot of standardized residuals (R's ``plot(fit, which = 2)``)."""
    from robstattm_py import plot
    return plot.qq(self, **kw)


def _plot_diagnostics(self: Any, **kw):
    """Four-panel diagnostic figure: residuals, Q-Q, scale-location, weights."""
    from robstattm_py import plot
    return plot.diagnostics(self, **kw)


# ---------- R-idiomatic accessor methods ---------------------------------
#
# R fit objects expose a standard S3 accessor family (`coef()`, `resid()`,
# `fitted()`, `weights()`, `vcov()`, `sigma()`). The per-class `coef()` was
# hand-written, but its siblings only existed as raw dataclass *fields*
# (`residuals`, `fitted_values`, `rweights`, `cov`, `scale`). These mixins give
# the regression results the missing R-idiomatic accessors, reading the
# already-materialised fields (no R round-trip). Method names are chosen to not
# collide with the underlying field names (hence `resid`, not `residuals`).


def _resid(self: Any) -> pd.Series:
    """Robust residuals as a pandas Series (R's ``resid()``/``residuals()``)."""
    return pd.Series(np.asarray(self.residuals).ravel(), name="residuals")


def _fitted(self: Any) -> pd.Series:
    """Fitted values as a pandas Series (R's ``fitted()``)."""
    return pd.Series(np.asarray(self.fitted_values).ravel(), name="fitted")


def _weights(self: Any) -> pd.Series:
    """Robustness weights as a pandas Series (R's ``weights()``).

    Reads ``rweights`` (or ``rweights_mm`` for the DCML fit).
    """
    w = getattr(self, "rweights", None)
    if w is None:
        w = getattr(self, "rweights_mm", None)
    return pd.Series(np.asarray(w).ravel(), name="weights")


def _vcov(self: Any) -> pd.DataFrame:
    """Coefficient covariance matrix as a labeled DataFrame (R's ``vcov()``)."""
    m = np.asarray(self.cov, dtype=float)
    names = getattr(self, "coef_names", None)
    if names is not None and len(names) == m.shape[0]:
        idx = list(names)
        return pd.DataFrame(m, index=idx, columns=idx)
    return pd.DataFrame(m)


def _sigma(self: Any) -> float:
    """Robust residual scale (R's ``sigma()``)."""
    return float(self.scale)


def _coef_df(self: Any) -> pd.Series:
    """Return ``coefficients`` as a pandas Series, indexed by coef name."""
    coefs = getattr(self, "coefficients", None)
    names = getattr(self, "coef_names", None)
    if coefs is None:
        raise AttributeError(
            f"{type(self).__name__} has no `coefficients` field — "
            "coef_df() is regression-only."
        )
    if names is None:
        names = [f"x{i}" for i in range(np.asarray(coefs).size)]
    return pd.Series(np.asarray(coefs).ravel(), index=list(names),
                     name="coefficients")


# ---------- installer -----------------------------------------------------

_INSTALLED = False


def install_result_mixins() -> None:
    """Attach ``to_dict`` / ``to_r`` / ``_repr_html_`` / ``coef_df`` to
    every result dataclass.

    Idempotent: subsequent calls are no-ops.  Called automatically once
    at package import time (see ``robstattm_py/__init__.py``).
    """
    global _INSTALLED
    if _INSTALLED:
        return

    # Lazy imports to avoid circular import (this module is imported by
    # __init__ which imports the wrapper modules below).
    from robstattm_py.covariance.cov_classic import CovClassicResult
    from robstattm_py.covariance.cov_rob import CovRobResult
    from robstattm_py.covariance.cov_rob_mm import CovRobMMResult
    from robstattm_py.covariance.cov_rob_rocke import CovRobRockeResult
    from robstattm_py.covariance.fastmve import FastMVEResult
    from robstattm_py.covariance.kurt_sd_new import KurtSDResult
    from robstattm_py.external.arima_rob import ArimaRobResult
    from robstattm_py.external.cubinf import CubinfResult
    from robstattm_py.external.glmrob import GlmrobResult
    from robstattm_py.external.gse import GSEResult, TSGSResult
    from robstattm_py.external.pense import PenseCVResult, PenseResult
    from robstattm_py.external.var_comprob import VarComprobResult
    from robstattm_py.glm.logreg import LogregResult
    from robstattm_py.pca.pca_rob_s import PcaRobSResult
    from robstattm_py.pca.prcomp_rob import PrcompRobResult
    from robstattm_py.regression.linear_test import RobLinearTestResult
    from robstattm_py.regression.lmrob_m import LmrobMResult
    from robstattm_py.regression.lmrobdet_dcml import LmrobdetDCMLResult
    from robstattm_py.regression.lmrobdet_mm import LmrobdetMMResult
    from robstattm_py.regression.pyinit import PyinitResult
    from robstattm_py.regression.refine_sm import RefineSMResult
    from robstattm_py.regression.step import StepResult
    from robstattm_py.univariate.loc_scale_m import LocScaleMResult

    all_results = [
        LmrobdetMMResult, LmrobdetDCMLResult, LmrobMResult, PyinitResult,
        StepResult, RobLinearTestResult, RefineSMResult,
        CovClassicResult, CovRobMMResult, CovRobRockeResult, CovRobResult,
        KurtSDResult, FastMVEResult,
        PcaRobSResult, PrcompRobResult,
        LogregResult, LocScaleMResult,
        PenseResult, PenseCVResult, GSEResult, TSGSResult,
        ArimaRobResult, VarComprobResult, GlmrobResult, CubinfResult,
    ]
    regression_results = {
        LmrobdetMMResult, LmrobdetDCMLResult, LmrobMResult, PyinitResult,
        LogregResult,
    }
    # Diagnostic plotting only works on lmrob* fits (need formula+data).
    diag_plot_results = {LmrobdetMMResult, LmrobdetDCMLResult, LmrobMResult}

    for cls in all_results:
        # Don't clobber methods the class already defines.
        if not hasattr(cls, "to_dict"):
            cls.to_dict = _result_to_dict
        if not hasattr(cls, "to_r"):
            cls.to_r = _result_to_r
        if not hasattr(cls, "_repr_html_"):
            cls._repr_html_ = _result_repr_html
        if cls in regression_results and not hasattr(cls, "coef_df"):
            cls.coef_df = _coef_df
        # R-idiomatic accessors, installed only where the backing field exists
        # and the class hasn't already defined the method. `hasattr(cls, field)`
        # is True for slotted dataclasses (the slot descriptor lives on the
        # class), so this correctly gates per-class.
        if cls in regression_results:
            if hasattr(cls, "residuals") and not hasattr(cls, "resid"):
                cls.resid = _resid
            if hasattr(cls, "fitted_values") and not hasattr(cls, "fitted"):
                cls.fitted = _fitted
            if (
                hasattr(cls, "rweights") or hasattr(cls, "rweights_mm")
            ) and not hasattr(cls, "weights"):
                cls.weights = _weights
            if hasattr(cls, "cov") and not hasattr(cls, "vcov"):
                cls.vcov = _vcov
            if hasattr(cls, "scale") and not hasattr(cls, "sigma"):
                cls.sigma = _sigma
        if cls in diag_plot_results:
            if not hasattr(cls, "plot_residuals"):
                cls.plot_residuals = _plot_residuals
            if not hasattr(cls, "plot_qq"):
                cls.plot_qq = _plot_qq
            if not hasattr(cls, "plot_diagnostics"):
                cls.plot_diagnostics = _plot_diagnostics

    _INSTALLED = True
