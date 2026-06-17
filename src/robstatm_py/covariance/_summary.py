"""Cov-side ``.summary()`` port — shared by ``covRob`` and ``covClassic``.

R's ``summary.covRob`` and ``summary.covClassic`` have identical bodies
(verified): both return ``(call, cov, center, evals, dist)`` when the
fit has no correlation matrix, or ``(call, cov, cor, center, evals)``
when it does. ``evals`` is the eigenvalues of ``cov`` (or of ``cor`` when
present), labelled ``"Eval. 1"`` … ``"Eval. p"``.

Per decision D-012 we expose this through a Python dataclass method
``.summary()`` on the result objects. Implementation strategy: delegate
to R via the stored ``_r_fit`` — strict-tier parity by construction.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from robstatm_py._r import r


@dataclass(frozen=True, slots=True)
class CovSummary:
    """Result of ``.summary()`` on a CovRob or CovClassic fit.

    Mirrors R's ``summary.covRob`` / ``summary.covClassic`` exactly.

    Attributes
    ----------
    cov : ndarray, shape (p, p)
        Robust (or classical) covariance matrix.
    center : ndarray, shape (p,)
        Location estimate.
    evals : ndarray, shape (p,)
        Eigenvalues of ``cov`` (or of ``cor`` if a correlation matrix was
        requested) — sorted by R from largest to smallest. R labels them
        ``"Eval. 1"`` … ``"Eval. p"``; the labels are exposed as
        :attr:`eval_names`.
    eval_names : tuple[str, ...]
        ``("Eval. 1", "Eval. 2", ...)``.
    dist : ndarray or None, shape (n,)
        Mahalanobis distances. ``None`` when R returns the
        ``cor``-variant of the summary (R drops ``dist`` from the
        summary list in that case).
    cor : ndarray or None, shape (p, p)
        Correlation matrix if the underlying fit was computed with
        ``corr=True``; otherwise ``None``.
    classical : bool
        ``True`` if this summarises a classical fit, ``False`` for
        robust. Useful for downstream pretty-printers.
    """

    cov: np.ndarray
    center: np.ndarray
    evals: np.ndarray
    eval_names: tuple[str, ...]
    dist: np.ndarray | None
    cor: np.ndarray | None
    classical: bool
    _r_summary: Any = field(default=None, repr=False, compare=False)

    @property
    def proportion_of_variance(self) -> np.ndarray:
        """Proportion of variance explained by each principal axis.

        Convenience: ``evals / sum(evals)``. Not a field returned by R's
        ``summary.cov*``, but trivial to derive from ``evals`` and useful
        for scree plotting. Computed in NumPy.
        """
        total = float(self.evals.sum())
        if total == 0.0:
            return np.zeros_like(self.evals)
        return self.evals / total

    def __repr__(self) -> str:
        kind = "Classical" if self.classical else "Robust"
        p = self.cov.shape[0]
        top = ", ".join(f"{v:.4g}" for v in self.evals[:3])
        more = ", ..." if self.evals.size > 3 else ""
        return f"<{kind}CovSummary: p={p}, evals=[{top}{more}]>"

    def _repr_html_(self) -> str:
        import pandas as pd
        rows = pd.DataFrame(
            {"Eigenvalue": self.evals,
             "Proportion": self.proportion_of_variance,
             "Cumulative": np.cumsum(self.proportion_of_variance)},
            index=list(self.eval_names),
        )
        kind = "Classical" if self.classical else "Robust"
        return (f"<h4>{kind} covariance summary "
                f"(p={self.cov.shape[0]}"
                f"{', n=' + str(self.dist.size) if self.dist is not None else ''})</h4>"
                + rows.to_html(float_format="{:.5g}".format))


def summary_of_cov(
    cov: np.ndarray,
    center: np.ndarray,
    dist: np.ndarray | None,
    cor: np.ndarray | None,
    *,
    classical: bool,
) -> CovSummary:
    """Replicate R's ``summary.covRob`` / ``summary.covClassic`` exactly.

    R's source for both methods (identical bodies, verified) is::

        evals <- eigen(if (is.null(cor)) cov else cor,
                       symmetric = TRUE, only.values = TRUE)$values
        names(evals) <- paste("Eval.", 1:length(evals))

    We push the already-extracted ``cov`` (or ``cor``) into R and call
    the same ``eigen()`` to guarantee bit-equal eigenvalues. The
    remaining summary fields are copies of the fit fields, which the R
    method also just copies.

    Parameters
    ----------
    cov, center : ndarray
        Already-extracted covariance and center from the fit.
    dist : ndarray or None
        Mahalanobis distances; ``None`` when the fit's ``cor`` is
        populated (R drops ``dist`` from the summary in that case).
    cor : ndarray or None
        Robust correlation matrix; ``None`` for the no-correlation case.
    classical : bool
        Marker bit for the result; doesn't affect numerics.
    """
    ro = r()
    target = cor if cor is not None else cov
    ro.globalenv["rpm_summ_target"] = target
    try:
        evals_r = ro.r(
            "eigen(rpm_summ_target, symmetric=TRUE, only.values=TRUE)$values"
        )
    finally:
        ro.r("if (exists('rpm_summ_target')) rm(rpm_summ_target)")
    evals = np.asarray(evals_r, dtype=float).ravel()
    eval_names = tuple(f"Eval. {i+1}" for i in range(evals.size))

    if cor is not None:
        dist_out: np.ndarray | None = None
    else:
        dist_out = dist

    return CovSummary(
        cov=np.asarray(cov, dtype=float),
        center=np.asarray(center, dtype=float).ravel(),
        evals=evals,
        eval_names=eval_names,
        dist=dist_out,
        cor=cor if cor is None else np.asarray(cor, dtype=float),
        classical=classical,
        _r_summary=None,
    )
