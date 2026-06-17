"""Peña–Prieto Kurtosis-SD highly robust initial estimator.

Wraps ``RobStatTM::KurtSDNew`` (alias ``initPP``). Maronna et al. (2019) §6.9.2.

This is the default initial estimator inside ``covRobMM`` and ``covRobRocke``;
expose it separately for users who want to chain custom refinement steps.

R return list: ``idx``, ``disma``, ``center``, ``cova``, ``t``.

**Determinism:** randomly samples projection directions — call
:func:`robstatm_py.set_seed` before for reproducibility.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from robstatm_py._converters import extract_array
from robstatm_py._r import r_pkg, rcall, rx2
from robstatm_py.covariance._common import validate_2d_numeric


@dataclass(frozen=True, slots=True)
class KurtSDResult:
    """Kurtosis-SD initial estimator output.

    Attributes
    ----------
    idx : ndarray, shape (n,)
        Subset-membership indicator (R: ``idx``).
    disma : ndarray, shape (n,)
        Squared Mahalanobis distances under the initial estimate.
    center : ndarray, shape (p,)
        Robust center.
    cova : ndarray, shape (p, p)
        Robust covariance estimate.
    t : ndarray, shape (n,)
        Final weights (R: ``t``).
    column_names : tuple[str, ...] | None
    """

    idx: np.ndarray
    disma: np.ndarray
    center: np.ndarray
    cova: np.ndarray
    t: np.ndarray
    column_names: tuple[str, ...] | None = None
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        return (
            f"<KurtSDResult: n={self.disma.shape[0]} p={self.center.shape[0]}>"
        )


def kurt_sd_new(
    X,
    *,
    muldirand: int = 20,
    muldifix: int = 10,
    dirmin: int = 1000,
) -> KurtSDResult:
    """Peña–Prieto kurtosis-driven robust initial estimator.

    Wraps ``RobStatTM::KurtSDNew`` (alias ``initPP``).

    Parameters
    ----------
    X : ndarray or pandas.DataFrame, shape (n, p)
    muldirand : int, default 20
        Random directions per random pass.
    muldifix : int, default 10
        Fixed directions per pass.
    dirmin : int, default 1000
        Lower bound on directions explored.

    Returns
    -------
    KurtSDResult

    Notes
    -----
    Call :func:`robstatm_py.set_seed` before for reproducibility.

    Examples
    --------
    >>> import robstatm_py as rpm
    >>> rpm.set_seed(7)
    >>> result = rpm.kurt_sd_new(rpm.datasets.wine())
    >>> result.center.shape
    (13,)
    """
    arr, col_names = validate_2d_numeric(X, name="X")
    pkg = r_pkg("RobStatTM")
    rfit = rcall(
        pkg.KurtSDNew,
        arr,
        muldirand=int(muldirand),
        muldifix=int(muldifix),
        dirmin=int(dirmin),
    )
    return KurtSDResult(
        idx=extract_array(rx2(rfit, "idx")).astype(float).ravel(),
        disma=extract_array(rx2(rfit, "disma")).astype(float).ravel(),
        center=extract_array(rx2(rfit, "center")).astype(float).ravel(),
        cova=np.asarray(rx2(rfit, "cova"), dtype=float),
        t=extract_array(rx2(rfit, "t")).astype(float).ravel(),
        column_names=col_names,
        _r_fit=rfit,
    )
