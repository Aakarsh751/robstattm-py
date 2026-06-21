"""Joint robust location and scale M-estimator.

Wraps ``RobStatTM::locScaleM`` (aliased ``MLocDis``); see Maronna et al.
(2019) §2.3 and §2.7. Depends on the R package ``RobStatTM`` only.

R return list captured at implementation time (RobStatTM 1.0.11):

    $ mu     : num
    $ std.mu : num
    $ disper : num

Field map:
    R name   ->   Python attribute
    mu       ->   mu
    std.mu   ->   std_mu
    disper   ->   disper
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from robstatm_py._converters import extract_float, validate_1d_numeric
from robstatm_py._r import r_pkg, rcall, rx2


@dataclass(frozen=True, slots=True)
class LocScaleMResult:
    """Result of :func:`loc_scale_m`.

    Attributes
    ----------
    mu : float
        Robust location estimate (R: ``mu``).
    std_mu : float
        Estimated standard error of ``mu`` (R: ``std.mu``).
    disper : float
        Robust scale (dispersion) estimate (R: ``disper``).
    """

    mu: float
    std_mu: float
    disper: float
    # Underlying rpy2 handle, exposed via ``.to_r()`` (installed by the result
    # mixins). Kept out of equality/repr so strict-tier comparisons are unaffected.
    _r_fit: Any = field(default=None, repr=False, compare=False)


# Allowed efficiencies per psi family, taken verbatim from R/MLocDis.R:
# the bisquare/huber branch tabulates eff in {0.85, 0.90, 0.95} (line ~58),
# while the opt/mopt branch uses {0.85, 0.90, 0.95, 0.99} (line ~92). R requires
# exact membership (``is.element`` / ``match``); an out-of-set eff yields an
# opaque error ("object 'resi' not found") or a silent NA fit, so we reject it
# in Python before the rpy2 boundary (implementation_rules: validate first).
_EFF_BY_FAMILY: dict[str, tuple[float, ...]] = {
    "bisquare": (0.85, 0.90, 0.95),
    "huber": (0.85, 0.90, 0.95),
    "opt": (0.85, 0.90, 0.95, 0.99),
    "mopt": (0.85, 0.90, 0.95, 0.99),
    "optv0": (0.85, 0.90, 0.95, 0.99),
    "moptv0": (0.85, 0.90, 0.95, 0.99),
}


def loc_scale_m(
    x,
    *,
    psi: Literal["mopt", "bisquare", "huber", "opt", "moptv0", "optv0"] = "mopt",
    eff: float = 0.95,
    maxit: int = 50,
    tol: float = 1e-4,
    na_rm: bool = False,
) -> LocScaleMResult:
    """Joint robust M-estimate of location and scale.

    Wraps ``RobStatTM::locScaleM`` (alias ``MLocDis``). Returns bit-for-bit
    identical values to the R function on the same input.

    Parameters
    ----------
    x : array_like, shape (n,)
        Univariate numeric sample. NaNs are not allowed unless ``na_rm=True``.
    psi : {"mopt", "bisquare", "huber", "opt", "moptv0", "optv0"}, default "mopt"
        ψ-family used by the IRLS step. ``"mopt"`` is the modified-optimal
        family recommended in Maronna et al. (2019, §2.7).
    eff : float, default 0.95
        Target Gaussian asymptotic efficiency. Common choices: 0.85, 0.90, 0.95.
    maxit : int, default 50
        Maximum IRLS iterations.
    tol : float, default 1e-4
        Convergence tolerance on the location update.
    na_rm : bool, default False
        If True, drop NaNs in ``x`` before fitting. If False (default) and ``x``
        contains NaNs, a ``ValueError`` is raised.

    Returns
    -------
    LocScaleMResult
        Frozen dataclass with fields ``mu``, ``std_mu``, ``disper``.

    Raises
    ------
    TypeError
        If ``x`` is not numeric.
    ValueError
        If ``x`` is empty, multi-dimensional, or contains NaNs with
        ``na_rm=False``.
    robstatm_py.RobStatTMSetupError
        If the RobStatTM R package is not installed.
    robstatm_py.RobStatTMRError
        If the underlying R call fails.

    Notes
    -----
    Thin rpy2 wrapper over ``RobStatTM::locScaleM``. The R alias ``MLocDis``
    refers to the same function. Outputs match R field-by-field to machine
    precision; see ``tests/univariate/test_loc_scale_m.py``.

    References
    ----------
    .. [1] Maronna, R. A., Martin, R. D., Yohai, V. J., & Salibian-Barrera, M.
       (2019). *Robust Statistics: Theory and Methods (with R)* (2nd ed.).
       Wiley. §2.3, §2.7.
    .. [2] RobStatTM R man page: ``?locScaleM``.

    Examples
    --------
    >>> from robstatm_py import loc_scale_m, set_seed
    >>> set_seed(123)
    >>> import numpy as np
    >>> x = np.concatenate([np.random.randn(20), [10.0, -10.0]])
    >>> res = loc_scale_m(x)
    >>> round(res.disper, 6)
    1.0
    """
    arr = validate_1d_numeric(x, name="x")
    has_nan = bool(np.isnan(arr).any())
    if has_nan and not na_rm:
        raise ValueError(
            "x contains NaN; pass na_rm=True to drop missing values"
        )
    # R's locScaleM only accepts a discrete set of efficiencies per family
    # (R/MLocDis.R). An out-of-set eff makes R fail with an opaque
    # "object 'resi' not found" error (bisquare/huber) or return a silent NA
    # (opt/mopt). Reject it here with a clear message instead.
    allowed_eff = _EFF_BY_FAMILY.get(psi)
    if allowed_eff is not None and float(eff) not in allowed_eff:
        raise ValueError(
            f"eff={eff} is not supported for psi={psi!r}; "
            f"allowed efficiencies are {allowed_eff}"
        )

    pkg = r_pkg("RobStatTM")
    rfit = rcall(
        pkg.locScaleM,
        arr,
        psi=psi,
        eff=float(eff),
        maxit=int(maxit),
        tol=float(tol),
        **{"na.rm": bool(na_rm)},
    )

    return LocScaleMResult(
        mu=extract_float(rx2(rfit, "mu")),
        std_mu=extract_float(rx2(rfit, "std.mu")),
        disper=extract_float(rx2(rfit, "disper")),
        _r_fit=rfit,
    )
