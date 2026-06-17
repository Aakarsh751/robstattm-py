"""Robust PCA via M-scale minimisation.

Wraps ``RobStatTM::pcaRobS`` (alias ``SMPCA``). Maronna et al. (2019) §6.11.2.
Depends on ``rrcov`` for the spherical-PCA initialisation.

R return list (RobStatTM 1.0.11): ``eigvec``, ``fit``, ``repre``, ``propex``,
``propSPC``, ``mu``, ``q``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from robstatm_py._converters import extract_array, extract_float, extract_int
from robstatm_py._r import r_pkg, rcall, rx2
from robstatm_py.covariance._common import validate_2d_numeric


@dataclass(frozen=True, slots=True)
class PcaRobSResult:
    """Robust PCA result.

    Attributes
    ----------
    eigvec : ndarray, shape (p, q)
        Robust principal directions (one per column, R: ``eigvec``).
    fit : ndarray, shape (n, p)
        Reconstructed (rank-q) fit of the data (R: ``fit``).
    repre : ndarray, shape (n, q)
        Scores: data projected onto the principal directions (R: ``repre``).
    propex : float
        Proportion of robust scale explained by the q components (R: ``propex``).
    prop_spc : ndarray, shape (p,)
        Per-direction proportions of robust scale (R: ``propSPC``).
    mu : ndarray, shape (p,)
        Robust center.
    q : int
        Number of retained components.
    column_names : tuple[str, ...] | None
    """

    eigvec: np.ndarray
    fit: np.ndarray
    repre: np.ndarray
    propex: float
    prop_spc: np.ndarray
    mu: np.ndarray
    q: int
    column_names: tuple[str, ...] | None = None
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        return (
            f"<PcaRobSResult: p={self.eigvec.shape[0]} q={self.q} "
            f"propex={self.propex:.4f}>"
        )


def pca_rob_s(
    X,
    *,
    ncomp: int | None = None,
    desprop: float = 0.9,
    deltasca: float = 0.5,
    maxit: int = 100,
) -> PcaRobSResult:
    """Robust PCA via M-scale minimisation.

    Wraps ``RobStatTM::pcaRobS``. Use :func:`robstatm_py.set_seed` immediately
    before calling for reproducibility.

    Parameters
    ----------
    X : ndarray or pandas.DataFrame, shape (n, p)
    ncomp : int, optional
        Number of components to extract. If None, the smallest q such that
        ``propSPC[1:q].sum() >= desprop`` is chosen.
    desprop : float, default 0.9
        Target cumulative proportion of robust scale (used when ``ncomp`` is None).
    deltasca : float, default 0.5
        M-scale tuning (breakdown point).
    maxit : int, default 100
        Inner-iteration cap.

    Returns
    -------
    PcaRobSResult

    Examples
    --------
    >>> import robstatm_py as rpm
    >>> rpm.set_seed(42)
    >>> result = rpm.pca_rob_s(rpm.datasets.bus(), ncomp=3)
    >>> result.q
    3
    """
    arr, col_names = validate_2d_numeric(X, name="X")
    pkg = r_pkg("RobStatTM")

    kwargs: dict = {"desprop": float(desprop), "deltasca": float(deltasca), "maxit": int(maxit)}
    if ncomp is not None:
        kwargs["ncomp"] = int(ncomp)

    rfit = rcall(pkg.pcaRobS, arr, **kwargs)

    return PcaRobSResult(
        eigvec=np.asarray(rx2(rfit, "eigvec"), dtype=float),
        fit=np.asarray(rx2(rfit, "fit"), dtype=float),
        repre=np.asarray(rx2(rfit, "repre"), dtype=float),
        propex=extract_float(rx2(rfit, "propex")),
        prop_spc=extract_array(rx2(rfit, "propSPC")).astype(float).ravel(),
        mu=extract_array(rx2(rfit, "mu")).astype(float).ravel(),
        q=extract_int(rx2(rfit, "q")),
        column_names=col_names,
        _r_fit=rfit,
    )
