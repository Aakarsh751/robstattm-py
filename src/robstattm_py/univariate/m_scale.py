"""Univariate robust M-scale estimator.

Wraps ``RobStatTM::scaleM`` (also exposed as ``mscale``); see Maronna et al.
(2019) §2.5–§2.6. Returns a single scalar — no dataclass needed.

R formals captured at implementation time (RobStatTM 1.0.11):

    function(u, delta=0.5, family="bisquare", max.it=100, tol=1e-6,
             tolerancezero=.Machine$double.eps,
             tuning.chi = lmrobdet.control(family=family, bb=delta)$tuning.chi)
"""
from __future__ import annotations

from typing import Literal

from robstattm_py._converters import extract_float, validate_1d_numeric
from robstattm_py._r import r_pkg, rcall


def m_scale(
    u,
    *,
    delta: float = 0.5,
    family: Literal["bisquare", "huber", "mopt", "opt", "moptv0", "optv0"] = "bisquare",
    max_it: int = 100,
    tol: float = 1e-6,
    tuning_chi: float | None = None,
) -> float:
    """Univariate M-scale.

    Wraps ``RobStatTM::scaleM``. Returns a Python float that is bit-for-bit
    identical to the R value on the same input.

    Parameters
    ----------
    u : array_like, shape (n,)
        Numeric vector (typically residuals).
    delta : float, default 0.5
        Breakdown-point parameter. Default 0.5 gives 50% breakdown.
    family : {"bisquare", "huber", "mopt", "opt", "moptv0", "optv0"}, default "bisquare"
        ρ-family.
    max_it : int, default 100
        Maximum iterations (R: ``max.it``).
    tol : float, default 1e-6
        Convergence tolerance.
    tuning_chi : float, optional
        Tuning constant for χ. If None, R's default is used
        (``lmrobdet.control(family=family, bb=delta)$tuning.chi``).

    Returns
    -------
    float
        The M-scale.

    Raises
    ------
    TypeError, ValueError
        On bad input. ``RobStatTMSetupError`` / ``RobStatTMRError`` if R or
        the package call fails.

    Notes
    -----
    The R name uses a dot (``max.it``); the Python name uses an underscore.
    See ``docs/user_interface.md §5``.

    References
    ----------
    .. [1] Maronna et al. (2019) §2.5–§2.6.
    .. [2] RobStatTM R man page: ``?scaleM``.

    Examples
    --------
    >>> from robstattm_py import m_scale, set_seed
    >>> set_seed(123)
    >>> import numpy as np
    >>> u = np.concatenate([np.random.randn(20), [10.0, -10.0]])
    >>> isinstance(m_scale(u), float)
    True
    """
    arr = validate_1d_numeric(u, name="u")
    if not (0.0 < float(delta) < 1.0):
        raise ValueError(f"delta must be in (0, 1); got {delta}")

    pkg = r_pkg("RobStatTM")

    kw: dict = {
        "delta": float(delta),
        "family": family,
        "tol": float(tol),
    }
    # R name has a dot — pass via kwargs map (rcall strips trailing _ already).
    kw["max.it"] = int(max_it)
    if tuning_chi is not None:
        kw["tuning.chi"] = float(tuning_chi)

    rval = rcall(pkg.scaleM, arr, **kw)
    return extract_float(rval)
