"""No-refit data extraction for native plots.

Native renderers consume **only** the arrays already on the frozen result
dataclasses (validated bit-for-bit against R, strict tier). They never re-fit in
R — that is the contract from decision D-023. The one documented exception is
leverage (``resid_vs_leverage``), which genuinely needs the hat matrix and is
fetched via ``fit.hatvalues()`` only when the caller does not supply it.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist

import numpy as np

from robstatm_py.plot._style import PlotStyle

_ND = NormalDist()


def _require_field(fit: object, name: str, plot_kind: str) -> object:
    v = getattr(fit, name, None)
    if v is None:
        raise TypeError(
            f"{type(fit).__name__} has no '{name}' field; native {plot_kind} "
            "plots expect a regression fit (lmrobdet_mm / lmrob_m / "
            "lmrobdet_dcml)."
        )
    return v


@dataclass
class RegData:
    """Plot-ready regression arrays (extracted, never re-fit)."""

    residuals: np.ndarray
    fitted: np.ndarray
    rweights: np.ndarray | None
    scale: float | None
    std_resid: np.ndarray
    n: int

    @property
    def index(self) -> np.ndarray:
        return np.arange(self.n)


def regression_data(fit: object) -> RegData:
    """Extract residuals / fitted / weights / standardized residuals from a fit."""
    resid = np.asarray(_require_field(fit, "residuals", "regression"), float).ravel()
    fitted = np.asarray(
        _require_field(fit, "fitted_values", "regression"), float
    ).ravel()

    rw = getattr(fit, "rweights", None)
    rweights = np.asarray(rw, float).ravel() if rw is not None else None

    scale_attr = getattr(fit, "scale", None)
    scale = float(scale_attr) if scale_attr not in (None, 0) else None

    if scale and scale > 0:
        std = resid / scale
    else:
        # Fall back to a robust scale of the residuals so the plot is still
        # meaningful for fits that don't expose ``scale``.
        mad = np.median(np.abs(resid - np.median(resid))) * 1.4826
        std = resid / mad if mad > 0 else resid
    return RegData(resid, fitted, rweights, scale, std, resid.size)


def flag_mask(data: RegData, style: PlotStyle) -> np.ndarray:
    """Boolean mask of points flagged as outliers under ``style``'s thresholds."""
    mask = np.zeros(data.n, dtype=bool)
    if data.rweights is not None:
        mask |= data.rweights < style.outlier_weight_thresh
    mask |= np.abs(data.std_resid) > style.outlier_resid_thresh
    return mask


def annotate_indices(
    data: RegData,
    style: PlotStyle,
    highlight=None,
    annotate: bool | None = None,
) -> list[int]:
    """Resolve which point indices to label (flagged ∪ user ``highlight``)."""
    do_outliers = style.annotate_outliers if annotate is None else annotate
    idx: set[int] = set()
    if do_outliers:
        idx.update(int(i) for i in np.nonzero(flag_mask(data, style))[0])
    if highlight is not None:
        idx.update(int(i) for i in highlight)
    return sorted(idx)


# ---------------------------------------------------------------------------
# multivariate / shared statistics (no scipy dependency required)
# ---------------------------------------------------------------------------

def chi2_quantile(p: float, df: int) -> float:
    """χ² quantile (inverse CDF).

    Uses ``scipy.stats.chi2.ppf`` when SciPy is importable (exact); otherwise
    falls back to the Wilson–Hilferty approximation, which is accurate to a few
    parts in 1e-3 for ``df >= 1`` — plenty for a reference-cutoff line.
    """
    try:
        from scipy.stats import chi2  # type: ignore

        return float(chi2.ppf(p, df))
    except Exception:
        z = _ND.inv_cdf(p)
        t = 1.0 - 2.0 / (9.0 * df) + z * np.sqrt(2.0 / (9.0 * df))
        return float(df * t**3)


def corr_from_cov(cov: np.ndarray) -> np.ndarray:
    """Correlation matrix derived from a covariance matrix."""
    cov = np.asarray(cov, float)
    d = np.sqrt(np.clip(np.diag(cov), 0.0, None))
    denom = np.outer(d, d)
    with np.errstate(invalid="ignore", divide="ignore"):
        corr = np.where(denom > 0, cov / denom, 0.0)
    return corr


def maha_distance(result: object) -> np.ndarray:
    """Return Mahalanobis distances (sqrt of the squared ``dist`` field)."""
    dist = getattr(result, "dist", None)
    if dist is None:
        raise TypeError(
            f"{type(result).__name__} has no 'dist' field; pass a covariance "
            "result computed with distances (e.g. cov_classic(..., distance=True))."
        )
    sq = np.asarray(dist, float).ravel()
    return np.sqrt(np.clip(sq, 0.0, None))


def pca_scores(pca: object) -> np.ndarray:
    """Component scores from a PCA result (``repre`` or ``scores``)."""
    for attr in ("repre", "scores"):
        v = getattr(pca, attr, None)
        if v is not None:
            return np.asarray(v, float)
    raise TypeError(
        f"{type(pca).__name__} has no scores; expected a pca_rob_s / prcomp_rob result"
    )


def pca_loadings(pca: object) -> np.ndarray:
    """Loadings / principal directions (``eigvec`` or ``rotation``), shape (p, q)."""
    for attr in ("eigvec", "rotation"):
        v = getattr(pca, attr, None)
        if v is not None:
            return np.asarray(v, float)
    raise TypeError(
        f"{type(pca).__name__} has no loadings; expected a pca_rob_s / prcomp_rob result"
    )


def pca_proportions(pca: object) -> np.ndarray:
    """Per-component proportion of (robust) variance / scale explained."""
    prop = getattr(pca, "prop_spc", None)
    if prop is not None:
        return np.asarray(prop, float).ravel()
    sdev = getattr(pca, "sdev", None)
    if sdev is not None:
        var = np.asarray(sdev, float).ravel() ** 2
        total = var.sum()
        return var / total if total > 0 else var
    raise TypeError(
        f"{type(pca).__name__} has no variance proportions (prop_spc / sdev)"
    )
