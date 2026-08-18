"""Robust R-squared inverse transform, ``RobStatTM::INVTR2``.

Pure-numeric helper used inside ``lmrobdetMM`` to convert the trimmed
quasi-R² into the reported robust R² value. Exported in RobStatTM's
NAMESPACE so users can call it directly.

R signature: ``INVTR2(RR2, family, cc)`` returning a scalar numeric.

``cc`` shape depends on the ψ-family. Empirically (RobStatTM 1.0.11):
  - ``"bisquare"``: scalar tuning constant.
  - ``"opt"``, ``"optv0"``, ``"mopt"``, ``"moptv0"``: 16-element vector
    (the family's standard rho-prime grid; e.g.
    ``robstattm_py.psi.mopt(0.95)`` for 95%-efficiency mopt).
  - ``"huber"``: internal code paths access ``cc[3]``, so scalar input
    produces NA limits inside ``integrate()``. Pass a 3-element tuning
    vector if you need huber here (rare, the textbook usage is bisquare
    or opt/mopt).
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from robstattm_py._r import r_pkg, rcall

_VALID_FAMILIES = {
    "bisquare", "huber", "mopt", "moptv0", "opt", "optv0",
}
_SCALAR_FAMILIES = {"bisquare"}
# Every family not in _SCALAR_FAMILIES takes a vector; the keys below are the
# authoritative list, so there is no separate set to keep in step with them.
_VECTOR_LEN_REQ = {  # required cc length per vector family
    "opt": 16, "optv0": 16, "mopt": 16, "moptv0": 16, "huber": 3,
}


def invtr2(rr2: float, family: str, cc: float | Sequence[float] | np.ndarray) -> float:
    """Port of ``RobStatTM::INVTR2``.

    Parameters
    ----------
    rr2 : float
        Raw trimmed quasi-R² statistic.
    family : str
        ψ-family name; one of ``"bisquare"``, ``"huber"``, ``"mopt"``,
        ``"moptv0"``, ``"opt"``, ``"optv0"``.
    cc : float or array-like
        ψ-family tuning constant(s). Scalar for ``"bisquare"``/``"huber"``;
        16-element vector for the opt/mopt families. Use
        ``robstattm_py.psi.<family>(efficiency)`` to compute the vector for
        a given efficiency target.

    Returns
    -------
    float
        Robust R² value implied by ``rr2`` under the given ρ.

    Examples
    --------
    >>> import robstattm_py as rpm
    >>> abs(rpm.invtr2(0.5, "bisquare", 4.685) - 0.5106142) < 1e-6
    True
    """
    if family not in _VALID_FAMILIES:
        raise ValueError(
            f"family must be one of {sorted(_VALID_FAMILIES)}; got {family!r}"
        )
    if not isinstance(rr2, (int, float)):
        raise TypeError(f"rr2 must be a real number; got {type(rr2).__name__}")

    if family in _SCALAR_FAMILIES:
        if not isinstance(cc, (int, float)):
            raise TypeError(
                f"cc must be a real number for family {family!r}; "
                f"got {type(cc).__name__}"
            )
        cc_arg: float | np.ndarray = float(cc)
    else:  # vector families
        cc_arr = np.asarray(cc, dtype=float).ravel()
        need = _VECTOR_LEN_REQ[family]
        if cc_arr.shape != (need,):
            raise ValueError(
                f"cc must be a length-{need} vector for family "
                f"{family!r}; got shape {cc_arr.shape}"
            )
        cc_arg = cc_arr

    pkg = r_pkg("RobStatTM")
    result = rcall(pkg.INVTR2, float(rr2), family, cc_arg)
    return float(result[0])
