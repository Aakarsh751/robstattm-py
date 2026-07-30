"""``refine.sm`` wrapper — concentrated-likelihood refinement step.

Wraps ``RobStatTM::refine.sm``. Given a candidate initial estimate
``(beta0, sigma0)``, ``refine.sm`` runs a short IRWLS / weighted-least-
squares loop using the ρ-family ``family`` with tuning constant ``cc``
and returns the refined coefficients and scale.

This is a **low-level building block** used inside the deterministic
initial estimator of ``lmrobdetMM``. End users normally don't call it
directly — they call :func:`lmrobdet_mm` and get the polished result.
We expose it here for parity with R's NAMESPACE.

R formals (RobStatTM 1.0.11)::

    refine.sm(x, y, initial.beta, initial.scale,
              k = 50, conv = 1, b, cc, family, step = "M", tol)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Sequence

import numpy as np

from robstattm_py._r import r_pkg, rcall, rx2
from robstattm_py._converters import extract_array, extract_bool, extract_float, extract_int


@dataclass(frozen=True, slots=True)
class RefineSMResult:
    """Output of :func:`refine_sm`.

    Attributes
    ----------
    beta : ndarray, shape (p,)
        Refined regression coefficients (R: ``beta.rw``).
    scale : float
        Refined scale estimate (R: ``scale.rw``).
    converged : bool
        Whether the IRWLS loop converged within ``k`` iterations.
    iterations : int
        Number of iterations actually used.
    """

    beta: np.ndarray
    scale: float
    converged: bool
    iterations: int
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        return (
            f"<RefineSMResult: p={self.beta.size}, scale={self.scale:.4g}, "
            f"converged={self.converged}, iter={self.iterations}>"
        )


def refine_sm(
    X: np.ndarray,
    y: np.ndarray,
    initial_beta: Sequence[float] | np.ndarray,
    initial_scale: float,
    *,
    b: float,
    cc: float | Sequence[float] | np.ndarray,
    family: Literal["bisquare", "opt", "mopt", "moptv0", "optv0", "huber"],
    k: int = 50,
    conv: int = 1,
    step: Literal["M", "S"] = "M",
    tol: float = 1e-7,
) -> RefineSMResult:
    """Refine an initial regression estimate via IRWLS.

    Wraps ``RobStatTM::refine.sm``. **Low-level helper** — most users
    want :func:`lmrobdet_mm`, which calls this internally.

    Parameters
    ----------
    X : ndarray, shape (n, p)
        Design matrix.
    y : ndarray, shape (n,)
        Response.
    initial_beta : array-like, shape (p,)
        Starting coefficients (e.g. from a high-breakdown S-step).
    initial_scale : float
        Starting scale estimate.
    b : float
        Tuning constant for the M-scale (``mscale``).
    cc : float or array-like
        Tuning constant for ``family`` — shape depends on the family
        (see :func:`robstattm_py.invtr2` for the family-shape table).
    family : str
        Name of the ρ family.
    k : int, default 50
        Maximum number of refinement iterations.
    conv : int, default 1
        Convergence flag (R's ``conv``; pass 1 for standard).
    step : {"M", "S"}, default "M"
        Refinement step type.
    tol : float, default 1e-7
        Convergence tolerance.

    Returns
    -------
    RefineSMResult

    Examples
    --------
    >>> import numpy as np, robstattm_py as rpm
    >>> rng = np.random.default_rng(0)
    >>> X = rng.standard_normal((50, 2))
    >>> y = X @ [1.0, 2.0] + rng.standard_normal(50) * 0.5
    >>> b_const = rpm.psi.bisquare(0.5)
    >>> cc_const = rpm.psi.bisquare(0.85)
    >>> res = rpm.refine_sm(X, y, initial_beta=[0.9, 1.9], initial_scale=0.5,
    ...                     b=float(b_const), cc=float(cc_const),
    ...                     family="bisquare")
    >>> res.beta.shape
    (2,)
    """
    X_arr = np.asarray(X, dtype=float)
    if X_arr.ndim != 2:
        raise ValueError(f"X must be 2-D; got shape {X_arr.shape}")
    y_arr = np.asarray(y, dtype=float).ravel()
    if y_arr.shape[0] != X_arr.shape[0]:
        raise ValueError(
            f"X has {X_arr.shape[0]} rows but y has length {y_arr.shape[0]}"
        )
    beta0 = np.asarray(initial_beta, dtype=float).ravel()
    if beta0.shape[0] != X_arr.shape[1]:
        raise ValueError(
            f"initial_beta has length {beta0.shape[0]}, "
            f"expected p={X_arr.shape[1]}"
        )

    cc_arg: float | np.ndarray
    if isinstance(cc, (int, float, np.floating, np.integer)):
        cc_arg = float(cc)
    else:
        cc_arg = np.asarray(cc, dtype=float).ravel()

    _ = r_pkg("RobStatTM")  # ensure loaded
    # Push the arrays as native R objects via globalenv so refine.sm sees them
    # as ordinary R matrices / vectors (no string round-trip, no inf/nan
    # formatting hazard, no quadratic R-command growth for large X). X is sent
    # as a flat column-major vector and reshaped in R with explicit dims so the
    # orientation is exact regardless of the input array's C/F memory layout.
    from robstattm_py._r import r as _rmod
    ro = _rmod()
    n_, p_ = X_arr.shape
    cc_is_vec = isinstance(cc_arg, np.ndarray)
    cleanup = [
        "rpm_refine_Xflat", "rpm_refine_X", "rpm_refine_y",
        "rpm_refine_b0", "rpm_refine_res",
    ]
    try:
        ro.globalenv["rpm_refine_Xflat"] = np.ascontiguousarray(
            X_arr.ravel(order="F")
        )
        ro.globalenv["rpm_refine_y"] = np.ascontiguousarray(y_arr)
        ro.globalenv["rpm_refine_b0"] = np.ascontiguousarray(beta0)
        # numpy2ri pushes a 1-D array as a *dim-attributed* R "array", not a
        # plain atomic vector — which breaks refine.sm's ``y - x %*% beta``
        # (array-vs-matrix dim mismatch -> "non-conformable"). Reshape X into a
        # real matrix and strip the dim attribute off the vectors via as.numeric.
        setup = (
            f"rpm_refine_X <- matrix(rpm_refine_Xflat, nrow={n_}, ncol={p_}); "
            "rpm_refine_y <- as.numeric(rpm_refine_y); "
            "rpm_refine_b0 <- as.numeric(rpm_refine_b0)"
        )
        if cc_is_vec:
            ro.globalenv["rpm_refine_cc"] = np.ascontiguousarray(cc_arg)
            cleanup.append("rpm_refine_cc")
            setup += "; rpm_refine_cc <- as.numeric(rpm_refine_cc)"
            cc_expr = "rpm_refine_cc"
        else:
            cc_expr = repr(float(cc_arg))
        ro.r(setup)
        cmd = (
            "rpm_refine_res <- refine.sm("
            "x=rpm_refine_X, y=rpm_refine_y, "
            "initial.beta=rpm_refine_b0, "
            f"initial.scale={float(initial_scale)}, "
            f"k={int(k)}, conv={int(conv)}, "
            f"b={float(b)}, cc={cc_expr}, "
            f"family='{family}', step='{step}', "
            f"tol={float(tol)})"
        )
        ro.r(cmd)
        rfit = ro.r("rpm_refine_res")
    finally:
        ro.r(
            "for (v in c(" + ",".join(f"'{v}'" for v in cleanup) + ")) "
            "if (exists(v)) rm(list=v)"
        )

    # R's refine.sm returns: beta.rw, scale.rw, converged, iterations.
    return RefineSMResult(
        beta=extract_array(rx2(rfit, "beta.rw")).astype(float).ravel(),
        scale=extract_float(rx2(rfit, "scale.rw")),
        converged=extract_bool(rx2(rfit, "converged")),
        iterations=extract_int(rx2(rfit, "iterations")),
        _r_fit=rfit,
    )
