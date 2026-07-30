"""Peña–Yohai highly robust initial estimator.

Wraps the **external** R package ``pyinit::pyinit``. Maronna et al. (2019)
§5.7. Returns a *matrix of candidate solutions* and their objective values.

R return list: ``coefficients`` (p × k), ``objective`` (length k).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from robstattm_py._converters import extract_array, validate_1d_numeric
from robstattm_py._errors import RobStatTMSetupError
from robstattm_py._r import r_pkg, rcall, rx2
from robstattm_py.covariance._common import validate_2d_numeric


@dataclass(frozen=True, slots=True)
class PyinitResult:
    """Peña–Yohai initial-estimator candidate set.

    Attributes
    ----------
    coefficients : ndarray, shape (p[+1], k)
        Candidate coefficient vectors as columns. k depends on tuning.
    objective : ndarray, shape (k,)
        Objective value (robust scale of residuals) for each candidate.
    best : ndarray, shape (p[+1],)
        Column of ``coefficients`` with the smallest objective. Convenience.
    """

    coefficients: np.ndarray
    objective: np.ndarray
    best: np.ndarray
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        return f"<PyinitResult: {self.coefficients.shape[1]} candidates, min obj={self.objective.min():.4g}>"


def pyinit(
    X,
    y,
    *,
    intercept: bool = True,
    delta: float = 0.5,
    cc: float = 1.5476,
    psc_keep: float = 0.5,
    resid_keep_method: Literal["threshold", "proportion"] = "threshold",
    resid_keep_prop: float = 0.2,
    resid_keep_thresh: float = 2.0,
    maxit: int = 10,
    eps: float = 1e-8,
    mscale_maxit: int = 200,
    mscale_tol: float | None = None,
    mscale_rho_fun: Literal["bisquare", "huber", "gauss"] = "bisquare",
) -> PyinitResult:
    """Peña–Yohai highly robust regression initial estimator.

    Wraps the external CRAN package ``pyinit::pyinit``.

    Parameters
    ----------
    X : ndarray or pandas.DataFrame, shape (n, p)
    y : array_like, shape (n,)
    intercept : bool, default True
    delta : float, default 0.5
    cc : float, default 1.5476
    psc_keep : float, default 0.5
    resid_keep_method : {"threshold", "proportion"}, default "threshold"
    resid_keep_prop : float, default 0.2
    resid_keep_thresh : float, default 2.0
    maxit : int, default 10
    eps : float, default 1e-8
    mscale_maxit : int, default 200
    mscale_tol : float, optional
        Inner M-scale tolerance. If None, R's default (= ``eps``) is used.
    mscale_rho_fun : {"bisquare", "huber", "gauss"}, default "bisquare"

    Returns
    -------
    PyinitResult

    Raises
    ------
    RobStatTMSetupError
        If the ``pyinit`` R package is not installed.

    Notes
    -----
    Deterministic: the Pena-Yohai construction does no random subsampling
    (no ``nsamp``/seed argument), so repeated calls on the same input are
    bit-for-bit identical without seeding. Verified against ``pyinit::pyinit``.
    """
    arr, _ = validate_2d_numeric(X, name="X")
    y_arr = validate_1d_numeric(y, name="y")
    if y_arr.shape[0] != arr.shape[0]:
        raise ValueError(
            f"y length {y_arr.shape[0]} != X rows {arr.shape[0]}"
        )

    try:
        pkg = r_pkg("pyinit")
    except RobStatTMSetupError:
        raise

    kwargs: dict = {
        "intercept": bool(intercept),
        "delta": float(delta),
        "cc": float(cc),
        "psc_keep": float(psc_keep),
        "resid_keep_method": resid_keep_method,
        "resid_keep_prop": float(resid_keep_prop),
        "resid_keep_thresh": float(resid_keep_thresh),
        "maxit": int(maxit),
        "eps": float(eps),
        "mscale_maxit": int(mscale_maxit),
        "mscale_rho_fun": mscale_rho_fun,
    }
    if mscale_tol is not None:
        kwargs["mscale_tol"] = float(mscale_tol)

    rfit = rcall(pkg.pyinit, arr, y_arr, **kwargs)
    coef = np.asarray(rx2(rfit, "coefficients"), dtype=float)
    obj = extract_array(rx2(rfit, "objective")).astype(float).ravel()
    # Reshape: R returns a matrix (p×k) for multi-candidate, may collapse to vector
    if coef.ndim == 1:
        coef = coef.reshape(-1, 1)
    best_col = int(np.argmin(obj))
    return PyinitResult(
        coefficients=coef,
        objective=obj,
        best=coef[:, best_col].copy(),
        _r_fit=rfit,
    )
