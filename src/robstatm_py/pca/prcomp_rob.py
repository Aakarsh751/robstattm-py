"""``prcomp``-shaped robust PCA wrapper.

Wraps ``RobStatTM::prcompRob``. Returns the same shape as base R ``prcomp``:
``sdev``, ``rotation``, ``center``, ``x``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from robstatm_py._converters import extract_array
from robstatm_py._r import r_pkg, rcall, rx2
from robstatm_py.covariance._common import validate_2d_numeric


@dataclass(frozen=True, slots=True)
class PrcompRobResult:
    """``prcomp``-shaped robust-PCA result.

    Attributes
    ----------
    sdev : ndarray, shape (p,)
        Robust standard deviations of the principal components.
    rotation : ndarray, shape (p, q)
        Loadings (R: ``rotation``).
    center : ndarray, shape (p,)
        Robust center.
    scores : ndarray, shape (n, q)
        Component scores (R: ``x`` — renamed for clarity).
    column_names : tuple[str, ...] | None
    """

    sdev: np.ndarray
    rotation: np.ndarray
    center: np.ndarray
    scores: np.ndarray
    column_names: tuple[str, ...] | None = None
    component_names: tuple[str, ...] | None = None
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        return f"<PrcompRobResult: q={self.rotation.shape[1]}, sdev={np.array2string(self.sdev[:3], precision=3)}...>"

    def summary(self):
        """Port of R's ``summary.prcompRob``.

        Returns
        -------
        :class:`robstatm_py.pca._summary.PrcompRobSummary`
            Includes the 3×p ``importance`` matrix (sdev / proportion /
            cumulative), rounded by R to 5 decimals.
        """
        from robstatm_py.pca._summary import summary_of_prcomp
        return summary_of_prcomp(self.sdev, self.component_names)


def prcomp_rob(
    X,
    *,
    rank: int | None = None,
    delta_scale: float = 0.5,
    max_iter: int = 100,
) -> PrcompRobResult:
    """Robust PCA, returned in base-R ``prcomp`` shape.

    Wraps ``RobStatTM::prcompRob``. Use :func:`robstatm_py.set_seed` before
    calling for reproducibility.

    Parameters
    ----------
    X : ndarray or pandas.DataFrame, shape (n, p)
    rank : int, optional
        Maximum rank (R kwarg ``rank.``).
    delta_scale : float, default 0.5
    max_iter : int, default 100

    Returns
    -------
    PrcompRobResult
    """
    arr, col_names = validate_2d_numeric(X, name="X")
    pkg = r_pkg("RobStatTM")
    kwargs: dict = {"delta.scale": float(delta_scale), "max.iter": int(max_iter)}
    if rank is not None:
        kwargs["rank."] = int(rank)
    rfit = rcall(pkg.prcompRob, arr, **kwargs)

    rotation = rx2(rfit, "rotation")
    rot_arr = np.asarray(rotation, dtype=float)
    # Component names from R's colnames(rotation) — used by summary().
    try:
        from robstatm_py._r import r as _r
        comp_names_raw = _r().r("colnames")(rotation)
        component_names: tuple[str, ...] | None = (
            tuple(comp_names_raw) if comp_names_raw is not None
            and hasattr(comp_names_raw, "__len__")
            and len(comp_names_raw) == rot_arr.shape[1] else None
        )
    except Exception:
        component_names = None

    return PrcompRobResult(
        sdev=extract_array(rx2(rfit, "sdev")).astype(float).ravel(),
        rotation=rot_arr,
        center=extract_array(rx2(rfit, "center")).astype(float).ravel(),
        scores=np.asarray(rx2(rfit, "x"), dtype=float),
        column_names=col_names,
        component_names=component_names,
        _r_fit=rfit,
    )
