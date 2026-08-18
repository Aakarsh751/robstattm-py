"""PCA-side ``.summary()`` port for :class:`PrcompRobResult`.

R's ``summary.prcompRob`` computes::

    vars       = sdev^2 / sum(sdev^2)
    importance = rbind(`Standard deviation`     = sdev,
                       `Proportion of Variance` = round(vars, 5),
                       `Cumulative Proportion`  = round(cumsum(vars), 5))

…and returns the fit augmented with ``importance``. We delegate to R via
the stored ``_r_fit`` for strict-tier parity (R does the rounding; we
read it back).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from robstattm_py._r import r


@dataclass(frozen=True, slots=True)
class PrcompRobSummary:
    """Result of ``PrcompRobResult.summary()``.

    Attributes
    ----------
    sdev : ndarray, shape (p,)
        Robust standard deviations of each principal component
        (echoed from the fit for convenience).
    proportion_of_variance : ndarray, shape (p,)
        ``round(sdev^2 / sum(sdev^2), 5)``, rounded by R.
    cumulative_proportion : ndarray, shape (p,)
        ``round(cumsum(proportion_of_variance), 5)``.
    importance : pandas.DataFrame, shape (3, p)
        Three rows ``"Standard deviation"`` / ``"Proportion of
        Variance"`` / ``"Cumulative Proportion"`` keyed by component
        names. Matches R's ``summary(prcompRob_fit)$importance``
        verbatim, including the rounding to 5 digits.
    component_names : tuple[str, ...]
        Column labels (``"PC 1"`` … ``"PC p"`` in R's convention).
    """

    sdev: np.ndarray
    proportion_of_variance: np.ndarray
    cumulative_proportion: np.ndarray
    importance: Any  # pandas.DataFrame
    component_names: tuple[str, ...]
    _r_summary: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        p = self.sdev.size
        top = ", ".join(f"{v:.4g}" for v in self.proportion_of_variance[:3])
        more = ", ..." if p > 3 else ""
        return f"<PrcompRobSummary: q={p}, prop_var=[{top}{more}]>"

    def _repr_html_(self) -> str:
        return ("<h4>Importance of components</h4>"
                + self.importance.to_html(float_format="{:.5g}".format))


def summary_of_prcomp(
    sdev: np.ndarray, component_names: tuple[str, ...] | None,
) -> PrcompRobSummary:
    """Replicate R's ``summary.prcompRob`` arithmetic exactly.

    R's source body is::

        vars       <- sdev^2
        vars       <- vars / sum(vars)
        importance <- rbind(`Standard deviation`     = sdev,
                            `Proportion of Variance` = round(vars, 5),
                            `Cumulative Proportion`  = round(cumsum(vars), 5))

    We push ``sdev`` into R, run the same expressions, and read the
    rounded vectors back, strict-tier identical to R's
    ``summary(prcompRob_fit)$importance`` (including the rounding to 5).
    """
    import pandas as pd

    ro = r()
    ro.globalenv["rpm_summ_sdev"] = np.asarray(sdev, dtype=float)
    try:
        ro.r(
            "rpm_summ_vars <- rpm_summ_sdev^2; "
            "rpm_summ_vars <- rpm_summ_vars / sum(rpm_summ_vars); "
            "rpm_summ_prop <- round(rpm_summ_vars, 5); "
            "rpm_summ_cum  <- round(cumsum(rpm_summ_vars), 5)"
        )
        prop = np.asarray(ro.r("rpm_summ_prop"), dtype=float).ravel()
        cum = np.asarray(ro.r("rpm_summ_cum"), dtype=float).ravel()
    finally:
        ro.r(
            "for (v in c('rpm_summ_sdev','rpm_summ_vars',"
            "'rpm_summ_prop','rpm_summ_cum'))"
            " if (exists(v)) rm(list=v)"
        )

    sdev_arr = np.asarray(sdev, dtype=float).ravel()
    p = sdev_arr.size
    if component_names is None or len(component_names) != p:
        col_names = tuple(f"PC {i+1}" for i in range(p))
    else:
        col_names = tuple(component_names)

    row_names = (
        "Standard deviation",
        "Proportion of Variance",
        "Cumulative Proportion",
    )
    importance = np.vstack([sdev_arr, prop, cum])
    importance_df = pd.DataFrame(
        importance, index=list(row_names), columns=list(col_names)
    )

    return PrcompRobSummary(
        sdev=sdev_arr,
        proportion_of_variance=prop,
        cumulative_proportion=cum,
        importance=importance_df,
        component_names=col_names,
        _r_summary=None,
    )
