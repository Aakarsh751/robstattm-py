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

def _plot_residuals(self: Any, **kw):
    from robstatm_py.plotting import residuals as _r
    return _r(self, **kw)


def _plot_qq(self: Any, **kw):
    from robstatm_py.plotting import qq as _q
    return _q(self, **kw)


def _plot_diagnostics(self: Any, **kw):
    from robstatm_py.plotting import diagnostics as _d
    return _d(self, **kw)


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
    at package import time (see ``robstatm_py/__init__.py``).
    """
    global _INSTALLED
    if _INSTALLED:
        return

    # Lazy imports to avoid circular import (this module is imported by
    # __init__ which imports the wrapper modules below).
    from robstatm_py.regression.lmrobdet_mm import LmrobdetMMResult
    from robstatm_py.regression.lmrobdet_dcml import LmrobdetDCMLResult
    from robstatm_py.regression.lmrob_m import LmrobMResult
    from robstatm_py.regression.pyinit import PyinitResult
    from robstatm_py.regression.step import StepResult
    from robstatm_py.regression.linear_test import RobLinearTestResult
    from robstatm_py.regression.refine_sm import RefineSMResult
    from robstatm_py.covariance.cov_classic import CovClassicResult
    from robstatm_py.covariance.cov_rob_mm import CovRobMMResult
    from robstatm_py.covariance.cov_rob_rocke import CovRobRockeResult
    from robstatm_py.covariance.cov_rob import CovRobResult
    from robstatm_py.covariance.kurt_sd_new import KurtSDResult
    from robstatm_py.covariance.fastmve import FastMVEResult
    from robstatm_py.pca.pca_rob_s import PcaRobSResult
    from robstatm_py.pca.prcomp_rob import PrcompRobResult
    from robstatm_py.glm.logreg import LogregResult
    from robstatm_py.univariate.loc_scale_m import LocScaleMResult
    from robstatm_py.external.pense import PenseResult, PenseCVResult
    from robstatm_py.external.gse import GSEResult, TSGSResult

    all_results = [
        LmrobdetMMResult, LmrobdetDCMLResult, LmrobMResult, PyinitResult,
        StepResult, RobLinearTestResult, RefineSMResult,
        CovClassicResult, CovRobMMResult, CovRobRockeResult, CovRobResult,
        KurtSDResult, FastMVEResult,
        PcaRobSResult, PrcompRobResult,
        LogregResult, LocScaleMResult,
        PenseResult, PenseCVResult, GSEResult, TSGSResult,
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
        if cls in diag_plot_results:
            if not hasattr(cls, "plot_residuals"):
                cls.plot_residuals = _plot_residuals
            if not hasattr(cls, "plot_qq"):
                cls.plot_qq = _plot_qq
            if not hasattr(cls, "plot_diagnostics"):
                cls.plot_diagnostics = _plot_diagnostics

    _INSTALLED = True
