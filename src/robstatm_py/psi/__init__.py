"""ψ-family infrastructure.

Wraps RobStatTM's exported ψ-family identifier functions (``bisquare``,
``huber``, ``mopt``, ``opt``, ``moptv0``, ``optv0``) and the ρ-evaluation
functions (``rho``, ``rhoprime``, ``rhoprime2``).

Each family identifier in R is a *function* that maps target Gaussian
efficiency ``e`` to a tuning constant ``cc`` (scalar for bisquare/huber,
vector for mopt/opt). The Python wrappers expose this directly:

>>> from robstatm_py.psi import bisquare, rho
>>> cc = bisquare(0.95)            # scalar tuning constant
>>> rho([-2, -1, 0, 1, 2], family="bisquare", cc=cc)  # doctest: +SKIP
array([0.45..., 0.13..., 0. , 0.13..., 0.45...])

See ``docs/research/psi_families.md``.
"""
from __future__ import annotations

from typing import Literal

import numpy as np

from robstatm_py._converters import extract_array, extract_float, validate_1d_numeric
from robstatm_py._r import r_pkg, rcall

Family = Literal["bisquare", "huber", "mopt", "opt", "moptv0", "optv0"]


def _tuning(family_name: str, e: float) -> np.ndarray | float:
    """Call the R family function with efficiency ``e``; return the tuning const(s)."""
    if not (0.0 < float(e) < 1.0):
        raise ValueError(f"efficiency must be in (0, 1); got {e}")
    pkg = r_pkg("RobStatTM")
    rfun = getattr(pkg, family_name)
    out = rcall(rfun, float(e))
    arr = extract_array(out)
    if arr.size == 1:
        return float(arr.ravel()[0])
    return arr.ravel()


def bisquare(e: float = 0.95) -> float:
    """Tuning constant of the bisquare ψ-family at target efficiency ``e``."""
    return _tuning("bisquare", e)  # type: ignore[return-value]


def huber(e: float = 0.95) -> float:
    """Tuning constant of the Huber ψ-family at target efficiency ``e``."""
    return _tuning("huber", e)  # type: ignore[return-value]


def mopt(e: float = 0.95) -> np.ndarray:
    """Tuning constant vector of the modified-optimal (m-opt) ψ-family."""
    out = _tuning("mopt", e)
    return np.asarray(out, dtype=float).ravel()


def opt(e: float = 0.95) -> np.ndarray:
    """Tuning constant vector of the Yohai optimal ψ-family."""
    out = _tuning("opt", e)
    return np.asarray(out, dtype=float).ravel()


def moptv0(e: float = 0.95) -> np.ndarray:
    """Tuning constant vector of the m-opt v0 calibration."""
    out = _tuning("moptv0", e)
    return np.asarray(out, dtype=float).ravel()


def optv0(e: float = 0.95) -> np.ndarray:
    """Tuning constant vector of the opt v0 calibration."""
    out = _tuning("optv0", e)
    return np.asarray(out, dtype=float).ravel()


# Map family name to (R function name, requires-vector-cc?)
_FAMILIES: dict[str, bool] = {
    "bisquare": False,
    "huber": False,
    "mopt": True,
    "opt": True,
    "moptv0": True,
    "optv0": True,
}


def _resolve_cc(family: Family, cc: float | np.ndarray | None, e: float | None) -> np.ndarray | float:
    """Pick a tuning constant: explicit ``cc`` wins, else compute from ``e``."""
    if cc is not None:
        if _FAMILIES[family] and np.ndim(cc) == 0:
            raise ValueError(
                f"family={family!r} requires a vector cc; pass e=… instead or provide a 1-D array"
            )
        return cc if np.ndim(cc) > 0 else float(cc)
    if e is None:
        e = 0.95
    fn = globals()[family]
    return fn(e)


def rho(
    u,
    *,
    family: Family = "bisquare",
    cc: float | np.ndarray | None = None,
    e: float | None = None,
    standardize: bool = True,
) -> np.ndarray:
    """Evaluate ρ(u) for the given ψ-family and tuning.

    Parameters
    ----------
    u : array_like
        Standardized residuals (or any numeric vector).
    family : {"bisquare","huber","mopt","opt","moptv0","optv0"}, default "bisquare"
        ψ-family.
    cc : float or ndarray, optional
        Tuning constant. Scalar for bisquare/huber; vector for mopt/opt families.
        If ``None``, computed from ``e``.
    e : float, optional
        Target Gaussian efficiency used to derive ``cc`` when ``cc is None``.
        Defaults to 0.95.
    standardize : bool, default True
        If True, ρ is scaled so that ρ(∞) = 1.

    Returns
    -------
    ndarray
        Element-wise ρ values, same shape as ``u``.

    Notes
    -----
    Wraps ``RobStatTM::rho``. Output matches R bit-for-bit.
    """
    arr = validate_1d_numeric(u, name="u")
    cc_v = _resolve_cc(family, cc, e)
    pkg = r_pkg("RobStatTM")
    out = rcall(pkg.rho, arr, family=family, cc=cc_v, standardize=bool(standardize))
    return extract_array(out).ravel().astype(float)


def rhoprime(
    u,
    *,
    family: Family = "bisquare",
    cc: float | np.ndarray | None = None,
    e: float | None = None,
    standardize: bool = False,
) -> np.ndarray:
    """Evaluate ψ(u) = ρ′(u) for the given family and tuning.

    See ``rho`` for parameter semantics.
    """
    arr = validate_1d_numeric(u, name="u")
    cc_v = _resolve_cc(family, cc, e)
    pkg = r_pkg("RobStatTM")
    out = rcall(pkg.rhoprime, arr, family=family, cc=cc_v, standardize=bool(standardize))
    return extract_array(out).ravel().astype(float)


def rhoprime2(
    u,
    *,
    family: Family = "bisquare",
    cc: float | np.ndarray | None = None,
    e: float | None = None,
    standardize: bool = False,
) -> np.ndarray:
    """Evaluate ψ′(u) = ρ″(u) for the given family and tuning."""
    arr = validate_1d_numeric(u, name="u")
    cc_v = _resolve_cc(family, cc, e)
    pkg = r_pkg("RobStatTM")
    out = rcall(pkg.rhoprime2, arr, family=family, cc=cc_v, standardize=bool(standardize))
    return extract_array(out).ravel().astype(float)


__all__ = [
    "bisquare", "huber", "mopt", "opt", "moptv0", "optv0",
    "rho", "rhoprime", "rhoprime2",
]
