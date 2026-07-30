"""Robust MM-regression wrapper.

Wraps ``RobStatTM::lmrobdetMM`` (Maronna et al. 2019 §5.3, §5.9). The flagship
robust-regression entry point in RobStatTM. Depends on the R packages
``RobStatTM``, ``pyinit`` (default S-initialization), and ``robustbase``
(τ-correction and leverage diagnostics).

R return list captured at implementation time (RobStatTM 1.0.11):

  coefficients (numeric, named)   scale (scalar)        residuals (n,)
  loss (scalar)                   converged (logical)   iter (int)
  fitted.values (n,)              rweights (n,)         control (list)
  init (S-fit object)             qr (qr object)        rank (int)
  cov (p×p matrix)                df.residual (int)     degree.freedom (int)
  iters.py (8,)                   scale.S (scalar)      iters.const (int)
  r.squared (scalar)              adj.r.squared (scalar)
  model (data.frame)              x (model matrix)      xlevels (list)
  call (call)                     terms (terms)         assign (int vec)

Public field map (R → Python):
  ``r.squared``     → ``r_squared``
  ``adj.r.squared`` → ``adj_r_squared``
  ``fitted.values`` → ``fitted_values``
  ``df.residual``   → ``df_residual``
  ``degree.freedom``→ ``degree_freedom``
  ``iters.py``      → ``iters_py``
  ``iters.const``   → ``iters_const``
  ``scale.S``       → ``scale_s``
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from robstattm_py._converters import (
    extract_array,
    extract_bool,
    extract_float,
    extract_int,
)
from robstattm_py._errors import RobStatTMRError
from robstattm_py._r import r, r_pkg, rcall, rx2, rx2_opt
from robstattm_py.regression._formula import coef_names_for, df_with_r_names
from robstattm_py.regression._s3_methods import (
    Drop1Result,
    LmrobdetMMPrediction,
    LmrobdetMMSummary,
    drop1_of,
    hatvalues_of,
    predict_of,
    rfpe_of,
    summary_of,
)
from robstattm_py.regression.control import LmrobdetControl, _control_to_r


@dataclass(frozen=True, slots=True)
class LmrobdetMMResult:
    """Result of :func:`lmrobdet_mm`.

    Field meanings mirror the R return list 1:1. Coefficient names are stored
    separately as ``coef_names`` because rpy2 strips the names attribute when
    converting to a numpy array.
    """

    coefficients: np.ndarray
    coef_names: tuple[str, ...]
    scale: float
    residuals: np.ndarray
    loss: float
    converged: bool
    iter: int
    fitted_values: np.ndarray
    rweights: np.ndarray
    rank: int
    cov: np.ndarray
    df_residual: int
    degree_freedom: int
    scale_s: float
    # R omits ``iters.const`` for some models (e.g. no-intercept formulas);
    # it is ``None`` in that case.
    iters_const: int | None
    r_squared: float
    adj_r_squared: float
    # Echo of inputs / R-side state — useful for downstream methods (summary,
    # predict) but not part of strict numerical comparison.
    formula: str
    control: LmrobdetControl
    _r_fit: Any = field(default=None, repr=False, compare=False)
    # Original data — used by step_lmrobdet / rob_linear_test to re-evaluate
    # the R-side fit (the converted _r_fit loses its S3 class on the rpy2
    # boundary, so we re-fit when downstream functions need the live R object).
    _data: Any = field(default=None, repr=False, compare=False)
    # Live R control list this fit used (``None`` ⇒ R defaults). The S3-method
    # ports refit in globalenv (the converted ``_r_fit`` has no S3 class), so
    # they must reuse the *same* control to reproduce this exact model.
    _r_control: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:  # short S3-print-equivalent
        cf = ", ".join(
            f"{n}={v:.4g}" for n, v in zip(self.coef_names, self.coefficients)
        )
        return (
            f"<LmrobdetMMResult: {self.formula} | {cf} | "
            f"scale={self.scale:.4g}, R²={self.r_squared:.3f}, "
            f"iter={self.iter}, converged={self.converged}>"
        )

    def coef(self) -> pd.Series:
        """Return coefficients as a named pandas Series."""
        return pd.Series(self.coefficients, index=list(self.coef_names), name="coef")

    # ----- S3 method ports (per project_memory/decisions.md D-012) -----
    # All three regression families share the same R S3 class
    # ("summary.lmrobdetMM"); the shared helpers in ``_s3_methods.py``
    # do the refit-on-R-side / dispatch / extract / cleanup dance.

    def summary(self) -> LmrobdetMMSummary:
        """Port of R's ``summary.lmrobdetMM``."""
        return summary_of(
            self.formula, self._data, self.coef_names, "lmrobdetMM",
            r_control=self._r_control,
        )

    def predict(
        self,
        newdata: pd.DataFrame | None = None,
        *,
        se_fit: bool = False,
    ) -> np.ndarray | LmrobdetMMPrediction:
        """Port of R's ``predict.lmrobdetMM`` (dispatched via ``robustbase``).

        Parameters
        ----------
        newdata : pandas.DataFrame, optional
            New data. If ``None``, returns in-sample predictions (equivalent
            to ``fitted_values``).
        se_fit : bool, default False
            If ``True``, return :class:`LmrobdetMMPrediction`.
        """
        return predict_of(
            self.formula, self._data, "lmrobdetMM", newdata, se_fit=se_fit,
            r_control=self._r_control,
        )

    def hatvalues(self) -> np.ndarray:
        """Port of R's ``hatvalues.lmrob`` — leverages of the fitted model."""
        return hatvalues_of(self.formula, self._data, "lmrobdetMM", r_control=self._r_control)

    def rfpe(self, *, both_vals: bool = False) -> float | tuple[float, float]:
        """Port of R's ``lmrobdetMM.RFPE`` — robust final prediction error.

        Parameters
        ----------
        both_vals : bool, default False
            If ``True``, return ``(min_rho_mm_c, penalty_rfpe)`` instead of
            their sum.
        """
        return rfpe_of(
            self.formula, self._data, both_vals=both_vals, r_control=self._r_control,
        )

    def drop1(self, scope=None, *, scale: float | None = None) -> Drop1Result:
        """Port of R's ``drop1.lmrobdetMM`` — single-term-deletion RFPE table.

        Recomputes the MM fit dropping each candidate term in turn and reports
        the Robust Final Prediction Error (RFPE) of the full model and of each
        sub-model, exactly as R's ``drop1(<lmrobdetMM>)`` does.

        Parameters
        ----------
        scope : sequence[str] or str, optional
            Term labels to consider for dropping. If ``None`` (default), every
            term is dropped (R's default behaviour). A single string is treated
            as one term label; it must be a subset of the model's term labels.
        scale : float, optional
            Residual scale estimate for the RFPE. If ``None``, the fit's own
            scale is used (R's default).

        Returns
        -------
        Drop1Result

        Notes
        -----
        ``drop1`` refits the MM model once per dropped term. ``lmrobdetMM`` uses
        the *deterministic* Pena-Yohai initial estimator (``pyinit``), so the
        result is reproducible without seeding and matches a direct
        ``drop1(lmrobdetMM(...))`` in R bit-for-bit.
        """
        if self._data is None:
            raise ValueError(
                "fit must have access to its original data to compute drop1; "
                "pass the DataFrame directly to lmrobdet_mm"
            )
        return drop1_of(
            self.formula, self._data, self._r_control, scope=scope, scale=scale,
        )


# Coefficient-name extraction moved to ``_formula.coef_names_for`` so
# all regression wrappers share one implementation.  See the docstring
# there for why we can't read names off the converted fit.


def lmrobdet_mm(
    formula: str | None = None,
    data: pd.DataFrame | None = None,
    *,
    X=None,
    y=None,
    control: LmrobdetControl | None = None,
    family: str | None = None,
    efficiency: float | None = None,
) -> LmrobdetMMResult:
    """Robust MM-regression via ``RobStatTM::lmrobdetMM``.

    Parameters
    ----------
    formula : str
        R-style formula, e.g. ``"zinc ~ copper"``.
    data : pandas.DataFrame
        Data frame containing the variables referenced in ``formula``.
    control : LmrobdetControl, optional
        Tuning parameter container. If None, defaults are used; if both
        ``control`` and ``family`` / ``efficiency`` are given, the kwargs
        override the corresponding control fields.
    family : str, optional
        Convenience shortcut for ``control.family``.
    efficiency : float, optional
        Convenience shortcut for ``control.efficiency``.

    Returns
    -------
    LmrobdetMMResult

    Raises
    ------
    TypeError, ValueError
        On bad input.
    robstattm_py.RobStatTMRError
        If the underlying R call fails.

    Notes
    -----
    Thin rpy2 wrapper around ``RobStatTM::lmrobdetMM``. Numeric outputs match
    R field-by-field to machine precision; see
    ``tests/regression/test_lmrobdet_mm.py``.

    Examples
    --------
    >>> import robstattm_py as rpm
    >>> df = rpm.datasets.mineral()
    >>> fit = rpm.lmrobdet_mm("zinc ~ copper", data=df)
    >>> fit.iter > 0
    True
    """
    from robstattm_py.regression._formula import resolve_formula_args
    formula, data = resolve_formula_args(formula, data, X=X, y=y)

    # Resolve control object
    base = control or LmrobdetControl()
    overrides: dict = {}
    if family is not None:
        overrides["family"] = family
    if efficiency is not None:
        overrides["efficiency"] = efficiency
    if overrides:
        from dataclasses import replace as _replace

        base = _replace(base, **overrides)

    ro = r()
    pkg = r_pkg("RobStatTM")

    # Push data to R as a data.frame. R rejects names starting with '_', so use 'rpm_data'.
    # When the DataFrame carries R column names in .attrs['r_columns'] (set by
    # robstattm_py.datasets loaders), restore them so the user can write the
    # formula in either Python or R column names — both work.
    data_for_r = data
    r_cols = data.attrs.get("r_columns") if hasattr(data, "attrs") else None
    if r_cols is not None and len(r_cols) == data.shape[1]:
        data_for_r = data.copy()
        data_for_r.columns = list(r_cols)
    ro.globalenv["rpm_data"] = data_for_r
    rformula = ro.Formula(formula)

    is_default = base == LmrobdetControl()
    # Build the R control list once (when non-default) so we can both fit with
    # it now and reuse the *same* object for the refit-based S3 methods later.
    r_control = None if is_default else _control_to_r(base)
    try:
        if r_control is None:
            r_fit = rcall(
                pkg.lmrobdetMM, rformula,
                data=ro.globalenv["rpm_data"],
                _hint="check data dtypes and column names",
            )
        else:
            r_fit = rcall(
                pkg.lmrobdetMM, rformula,
                data=ro.globalenv["rpm_data"], control=r_control,
                _hint="check data dtypes and column names",
            )
        # Extract coef names while rpm_data is still in globalenv —
        # model.matrix(formula, data=rpm_data) needs the data to
        # resolve dot formulas like "Y ~ .".
        coef_names = coef_names_for(formula)
    finally:
        ro.r('rm(rpm_data)')

    # Pull fields — handle NamedList / ListVector uniformly via rx2()
    coef_arr = extract_array(rx2(r_fit, "coefficients")).astype(float).ravel()

    return LmrobdetMMResult(
        coefficients=coef_arr,
        coef_names=coef_names,
        scale=extract_float(rx2(r_fit, "scale")),
        residuals=extract_array(rx2(r_fit, "residuals")).astype(float).ravel(),
        loss=extract_float(rx2(r_fit, "loss")),
        converged=extract_bool(rx2(r_fit, "converged")),
        iter=extract_int(rx2(r_fit, "iter")),
        fitted_values=extract_array(rx2(r_fit, "fitted.values")).astype(float).ravel(),
        rweights=extract_array(rx2(r_fit, "rweights")).astype(float).ravel(),
        rank=extract_int(rx2(r_fit, "rank")),
        cov=np.asarray(rx2(r_fit, "cov"), dtype=float),
        df_residual=extract_int(rx2(r_fit, "df.residual")),
        degree_freedom=extract_int(rx2(r_fit, "degree.freedom")),
        scale_s=extract_float(rx2(r_fit, "scale.S")),
        # ``iters.const`` is absent for some models (e.g. no-intercept fits).
        iters_const=(
            extract_int(_ic) if (_ic := rx2_opt(r_fit, "iters.const")) is not None
            else None
        ),
        r_squared=extract_float(rx2(r_fit, "r.squared")),
        adj_r_squared=extract_float(rx2(r_fit, "adj.r.squared")),
        formula=formula,
        control=base,
        _r_fit=r_fit,
        # Defensive copy: the result is a frozen dataclass, and its S3-method
        # ports (summary/predict/hatvalues/drop1) re-fit from this DataFrame.
        # Storing a snapshot keeps those methods stable even if the caller
        # later mutates the original frame.
        _data=data.copy(),
        _r_control=r_control,
    )


def drop1_lmrobdet(
    fit: LmrobdetMMResult,
    scope=None,
    *,
    scale: float | None = None,
) -> Drop1Result:
    """Single-term-deletion RFPE table for an ``lmrobdetMM`` fit.

    Module-level convenience equivalent to :meth:`LmrobdetMMResult.drop1`;
    port of R's ``drop1.lmrobdetMM``.

    Parameters
    ----------
    fit : LmrobdetMMResult
        A fit produced by :func:`lmrobdet_mm` (must carry its original data).
    scope : sequence[str] or str, optional
        Term labels to consider for dropping; ``None`` drops all terms.
    scale : float, optional
        Residual scale for the RFPE; defaults to the fit's own scale.

    Returns
    -------
    Drop1Result

    Examples
    --------
    >>> import robstattm_py as rpm
    >>> fit = rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())
    >>> tbl = rpm.drop1_lmrobdet(fit)
    >>> "<none>" in tbl.terms
    True
    """
    if not isinstance(fit, LmrobdetMMResult):
        raise TypeError("fit must be a LmrobdetMMResult")
    return fit.drop1(scope=scope, scale=scale)
