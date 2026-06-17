"""Classical Pearson covariance via ``RobStatTM::covClassic``.

Returned shape mirrors the robust ``covRobMM``/``covRobRocke`` results so
helpers like ``distance_distance(robust, classical)`` work generically.

R return list (RobStatTM 1.0.11): ``center``, ``cov``, ``cor``, ``dist``, ``call``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from robstatm_py._converters import extract_array
from robstatm_py._r import r_pkg, rcall, rx2
from robstatm_py.covariance._common import validate_2d_numeric


@dataclass(frozen=True, slots=True)
class CovClassicResult:
    """Classical covariance result.

    Attributes
    ----------
    center : ndarray, shape (p,)
    cov : ndarray, shape (p, p)
    cor : ndarray, shape (p, p) or None
        Correlation matrix; None unless ``corr=True``.
    dist : ndarray, shape (n,)
        Squared Mahalanobis distances when ``distance=True``.
    column_names : tuple[str, ...] | None
    classical : bool
        Always True; lets generic helpers tell us apart from robust results.
    """

    center: np.ndarray
    cov: np.ndarray
    cor: np.ndarray | None
    dist: np.ndarray | None
    column_names: tuple[str, ...] | None = None
    classical: bool = True
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        p = self.cov.shape[0]
        return f"<CovClassicResult: p={p}, center={np.array2string(self.center, precision=4)}>"

    def summary(self):
        """Port of R's ``summary.covClassic``.

        The R bodies of ``summary.covRob`` and ``summary.covClassic`` are
        identical, so this delegates to the same helper with
        ``classical=True``.

        Returns
        -------
        :class:`robstatm_py.covariance._summary.CovSummary`
        """
        from robstatm_py.covariance._summary import summary_of_cov
        return summary_of_cov(
            self.cov, self.center, self.dist, self.cor, classical=True,
        )


def _maybe_array(rval) -> np.ndarray | None:
    if rval is None:
        return None
    try:
        arr = np.asarray(rval, dtype=float)
    except Exception:
        return None
    if arr.size == 0:
        return None
    return arr


_NA_ACTION_RFUN = {"fail": "na.fail", "omit": "na.omit", "pass": "na.pass"}


def cov_classic(
    X,
    *,
    corr: bool = False,
    center: bool = True,
    distance: bool = True,
    na_action: str | None = None,
    unbiased: bool = True,
) -> CovClassicResult:
    """Classical (Pearson) mean and covariance.

    Wraps ``RobStatTM::covClassic``. The return shape mirrors the robust
    estimators so generic helpers work transparently.

    Parameters
    ----------
    X : ndarray or pandas.DataFrame, shape (n, p)
    corr : bool, default False
        Return the correlation matrix in ``cor``.
    center : bool, default True
        Center the data when computing the covariance.
    distance : bool, default True
        Compute Mahalanobis distances.
    na_action : {"fail", "omit", "pass"}, optional
        How to handle missing (NaN) entries, mapped to R's ``na.fail`` /
        ``na.omit`` / ``na.pass``. The default (``None``) uses R's default
        ``na.fail``, which raises if any NaN is present. Pass ``"omit"`` to
        drop rows containing NaN before estimation (the result then has
        ``n_complete`` rows of ``dist``).
    unbiased : bool, default True
        Use (n-1) denominator when True; n when False.

    Returns
    -------
    CovClassicResult

    Examples
    --------
    >>> import robstatm_py as rpm
    >>> df = rpm.datasets.wine()
    >>> result = rpm.cov_classic(df)
    >>> result.center.shape
    (13,)
    """
    if na_action is not None and na_action not in _NA_ACTION_RFUN:
        raise ValueError(
            f"na_action must be one of {sorted(_NA_ACTION_RFUN)} or None; "
            f"got {na_action!r}"
        )
    # Only "omit"/"pass" can tolerate NaN; "fail"/None must reject it (matching
    # R's na.fail). Let NaN through to R only when the action will handle it.
    allow_nan = na_action in {"omit", "pass"}
    arr, col_names = validate_2d_numeric(X, name="X", allow_nan=allow_nan)

    pkg = r_pkg("RobStatTM")
    kwargs: dict = dict(
        corr=bool(corr),
        center=bool(center),
        distance=bool(distance),
        unbiased=bool(unbiased),
    )
    if na_action is not None:
        from robstatm_py._r import r as _r
        kwargs["na.action"] = _r().r(_NA_ACTION_RFUN[na_action])
    rfit = rcall(pkg.covClassic, arr, **kwargs)

    return CovClassicResult(
        center=extract_array(rx2(rfit, "center")).astype(float).ravel(),
        cov=np.asarray(rx2(rfit, "cov"), dtype=float),
        cor=_maybe_array(rx2(rfit, "cor")),
        dist=_maybe_array(rx2(rfit, "dist")),
        column_names=col_names,
        _r_fit=rfit,
    )
