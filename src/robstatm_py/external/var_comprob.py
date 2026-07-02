"""Robust variance-component / mixed-model estimation — wraps ``robustvarComp``.

Maronna et al. (2019) §6.x (autism growth-model example). Composite robust
S/Tau/MM estimators for linear mixed / variance-component models. Requires the
CRAN package ``robustvarComp`` (installed separately; see
``robstatm_py.check_setup()``).

Two entry points, mirroring the R API:

* :func:`var_comprob_control` → ``robustvarComp::varComprob.control``
* :func:`var_comprob`         → ``robustvarComp::varComprob``

``varComprob`` is *stochastic* (default ``fixed.init="lmrob.S"`` /
``cov.init="TSGS"``). Call :func:`robstatm_py.set_seed` before for
reproducibility. We fit *inside* R-space (push the data frame, ``groups`` matrix,
``varcov`` kernels and control to ``globalenv``) so the result equals R exactly.

Note: a plain ``data.frame`` produces results numerically identical to an
``nlme::groupedData`` object (verified, diff = 0) — the ``groups`` matrix drives
the grouping — so this wrapper does not require ``nlme``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np
import pandas as pd

from robstatm_py._converters import extract_array
from robstatm_py._r import r, require_r_pkg

# python-kwarg → R-arg name for varComprob.control
_CONTROL_R_NAMES = {
    "init": "init",
    "lower": "lower",
    "upper": "upper",
    "epsilon": "epsilon",
    "tuning_chi": "tuning.chi",
    "bb": "bb",
    "tuning_psi": "tuning.psi",
    "arp_chi": "arp.chi",
    "arp_psi": "arp.psi",
    "max_it": "max.it",
    "rel_tol_beta": "rel.tol.beta",
    "rel_tol_gamma": "rel.tol.gamma",
    "rel_tol_scale": "rel.tol.scale",
    "trace_lev": "trace.lev",
    "method": "method",
    "psi": "psi",
    "beta_univ": "beta.univ",
    "gamma_univ": "gamma.univ",
    "fixed_init": "fixed.init",
    "cov_init": "cov.init",
    "cov": "cov",
}


@dataclass(frozen=True, slots=True)
class VarComprobControl:
    """Tuning parameters for :func:`var_comprob` (``varComprob.control``).

    Holds only the arguments the caller set explicitly (as ``{R_name: value}``);
    everything else falls back to R's ``varComprob.control`` defaults.
    """

    args: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        method = self.args.get("method", "compositeTau")
        psi = self.args.get("psi", "optimal")
        return f"<VarComprobControl method={method!r} psi={psi!r}>"


def var_comprob_control(
    *,
    method: str | None = None,
    psi: str | None = None,
    lower: float | Sequence[float] | None = None,
    upper: float | Sequence[float] | None = None,
    cov_init: str | None = None,
    fixed_init: str | None = None,
    epsilon: float | None = None,
    max_it: int | None = None,
    beta_univ: bool | None = None,
    gamma_univ: bool | None = None,
    cov: bool | None = None,
    **extra: Any,
) -> VarComprobControl:
    """Build a control object for :func:`var_comprob` (``varComprob.control``).

    Only explicitly-passed arguments are forwarded; the rest use R's defaults
    (``method="compositeTau"``, ``psi="optimal"``, ``cov.init="TSGS"``,
    ``fixed.init="lmrob.S"``, ``lower=0``, ``upper=Inf``, ...).

    Parameters
    ----------
    method : {"compositeTau","compositeS","compositeMM","Tau","S","MM"}, optional
    psi : {"optimal","bisquare","rocke"}, optional
    lower, upper : float or sequence of float, optional
        Box constraints on the variance-component parameters. ``-inf`` / ``inf``
        map to R ``-Inf`` / ``Inf``.
    cov_init : {"TSGS","2SGS","covOGK"}, optional
    fixed_init : {"lmrob.S","lmRob"}, optional
    epsilon, max_it, beta_univ, gamma_univ, cov : optional
    **extra
        Any other ``varComprob.control`` argument by its Python name
        (e.g. ``rel_tol_beta``, ``arp_chi``, ``trace_lev``).

    Returns
    -------
    VarComprobControl
    """
    raw = {
        "method": method, "psi": psi, "lower": lower, "upper": upper,
        "cov_init": cov_init, "fixed_init": fixed_init, "epsilon": epsilon,
        "max_it": max_it, "beta_univ": beta_univ, "gamma_univ": gamma_univ,
        "cov": cov, **extra,
    }
    args: dict[str, Any] = {}
    for py_name, val in raw.items():
        if val is None:
            continue
        r_name = _CONTROL_R_NAMES.get(py_name)
        if r_name is None:
            raise ValueError(f"unknown varComprob.control argument: {py_name!r}")
        args[r_name] = val
    return VarComprobControl(args=args)


@dataclass(frozen=True, slots=True)
class VarComprobResult:
    """Robust variance-component fit (``robustvarComp::varComprob``).

    Attributes
    ----------
    beta : ndarray, shape (n_fixef,)
        Fixed-effect coefficients.
    beta_names : tuple[str, ...]
    vcov_beta : ndarray, shape (n_fixef, n_fixef)
    eta : ndarray, shape (n_varcomp,)
        Variance-component parameters (one per ``varcov`` kernel).
    eta_names : tuple[str, ...]
    vcov_eta : ndarray
    gamma : ndarray, shape (n_varcomp,)
        Reparameterised variance components.
    vcov_gamma : ndarray
    sigma2 : float
        Error variance.
    Sigma : ndarray, shape (p, p)
        Estimated within-group covariance.
    scales : ndarray
        Composite per-pair scales; **empty** for the non-composite ``method="S"``
    min : float
        Final objective value.
    iterations : int
    method : str
    """

    beta: np.ndarray
    beta_names: tuple[str, ...]
    vcov_beta: np.ndarray
    eta: np.ndarray
    eta_names: tuple[str, ...]
    vcov_eta: np.ndarray
    gamma: np.ndarray
    vcov_gamma: np.ndarray
    sigma2: float
    Sigma: np.ndarray
    scales: np.ndarray
    min: float
    iterations: int
    method: str
    _r_fit: Any = field(default=None, repr=False, compare=False)

    def __repr__(self) -> str:
        return (
            f"<VarComprobResult: method={self.method!r} "
            f"n_fixef={self.beta.shape[0]} n_varcomp={self.eta.shape[0]} "
            f"sigma2={self.sigma2:.4g}>"
        )


def _r_logical(b: bool) -> str:
    return "TRUE" if b else "FALSE"


def _opt_arr(ro, expr: str) -> np.ndarray:
    """Read an array that may be NULL (e.g. `scales` is NULL for method='S')."""
    if bool(ro.r(f"is.null({expr})")[0]):
        return np.empty(0)
    return extract_array(ro.r(expr)).astype(float).ravel()


def _push_control(ro, control: VarComprobControl | None, pushed: list[str]) -> str:
    """Build a ``varComprob.control(...)`` call string, pushing vector args to R.

    Namespace-qualified (``robustvarComp::``) because the package is loaded but
    *not attached* (see :func:`robstatm_py._r.require_r_pkg`).
    """
    if control is None or not control.args:
        return "robustvarComp::varComprob.control()"
    parts: list[str] = []
    for i, (r_name, val) in enumerate(control.args.items()):
        if isinstance(val, bool):
            parts.append(f"`{r_name}`={_r_logical(val)}")
        elif isinstance(val, str):
            parts.append(f"`{r_name}`={val!r}".replace("'", '"'))
        elif np.isscalar(val):
            parts.append(f"`{r_name}`={float(val)}")
        else:  # vector (lower/upper/init/tuning.*)
            arr = np.asarray(val, dtype=float).ravel()
            vname = f"rpm_vc_ctrl_{i}"
            ro.globalenv[vname] = arr
            pushed.append(vname)
            parts.append(f"`{r_name}`={vname}")
    return f"robustvarComp::varComprob.control({', '.join(parts)})"


def var_comprob(
    fixed: str,
    data: "pd.DataFrame",
    *,
    groups: np.ndarray,
    varcov: Sequence[np.ndarray],
    varcov_names: Sequence[str] | None = None,
    control: VarComprobControl | None = None,
) -> VarComprobResult:
    """Robust variance-component estimation (``robustvarComp::varComprob``).

    Parameters
    ----------
    fixed : str
        Fixed-effects formula, e.g.
        ``"vsae ~ age.2 + I(age.2^2) + sicdegp2.f + age.2:sicdegp2.f + I(age.2^2):sicdegp2.f"``.
        Factor terms must be categorical columns of ``data``.
    data : pandas.DataFrame
        Model data. Categorical columns become R factors.
    groups : ndarray, shape (n_obs, 2)
        Integer grouping matrix: column 0 the within-group index, column 1 the
        group id. For balanced data, ``cbind(rep(1:p, each=n), rep(1:n, p))``.
    varcov : sequence of ndarray
        The ``K`` list of ``p×p`` covariance kernels.
    varcov_names : sequence of str, optional
        Names for the kernels (defaults to R positional names).
    control : VarComprobControl, optional
        From :func:`var_comprob_control`. Defaults to Composite-Tau / optimal psi.

    Returns
    -------
    VarComprobResult

    Raises
    ------
    robstatm_py.RobStatTMSetupError
        If the ``robustvarComp`` R package is not installed.

    Notes
    -----
    Stochastic — call :func:`robstatm_py.set_seed` before for reproducibility.
    """
    require_r_pkg("robustvarComp")  # ensure installed (namespace only; no attach)
    ro = r()

    groups_arr = np.asarray(groups)
    if groups_arr.ndim != 2 or groups_arr.shape[1] != 2:
        raise ValueError("`groups` must be an (n_obs, 2) integer matrix")

    pushed: list[str] = []
    try:
        ro.globalenv["rpm_vc_df"] = data
        pushed.append("rpm_vc_df")
        ro.globalenv["rpm_vc_groups"] = groups_arr.astype(float)
        pushed.append("rpm_vc_groups")
        # storage.mode integer so varComprob sees an integer matrix
        ro.r("storage.mode(rpm_vc_groups) <- 'integer'")

        # Build the K list in R from the pushed kernels.
        for i, kern in enumerate(varcov):
            karr = np.asarray(kern, dtype=float)
            vname = f"rpm_vc_K_{i}"
            ro.globalenv[vname] = karr
            pushed.append(vname)
        k_refs = ", ".join(f"rpm_vc_K_{i}" for i in range(len(varcov)))
        ro.r(f"rpm_vc_K <- list({k_refs})")
        pushed.append("rpm_vc_K")
        if varcov_names is not None:
            names_r = "c(" + ", ".join(f'"{n}"' for n in varcov_names) + ")"
            ro.r(f"names(rpm_vc_K) <- {names_r}")

        ctrl_expr = _push_control(ro, control, pushed)
        ro.r(f"rpm_vc_ctrl <- {ctrl_expr}")
        pushed.append("rpm_vc_ctrl")

        ro.r(
            f"rpm_vc_fit <- robustvarComp::varComprob({fixed}, "
            f"groups=rpm_vc_groups, data=rpm_vc_df, varcov=rpm_vc_K, "
            f"control=rpm_vc_ctrl)"
        )
        pushed.append("rpm_vc_fit")

        # Extract fields one at a time via `$` access. Converting the *whole*
        # fit object (`ro.r("rpm_vc_fit")`) would push its embedded `model`
        # data.frame / `terms` through the active pandas2ri converter and crash
        # ("Per-column arrays must each be 1-dimensional") — same fragility as
        # the pense cvfit (see pense.py / discoveries.md).
        beta = extract_array(ro.r("rpm_vc_fit$beta")).astype(float).ravel()
        eta = extract_array(ro.r("rpm_vc_fit$eta")).astype(float).ravel()
        gamma = extract_array(ro.r("rpm_vc_fit$gamma")).astype(float).ravel()
        method = str(ro.r("rpm_vc_fit$control$method")[0])

        result = VarComprobResult(
            beta=beta,
            beta_names=tuple(str(n) for n in ro.r("names(rpm_vc_fit$beta)")),
            vcov_beta=np.asarray(ro.r("rpm_vc_fit$vcov.beta"), dtype=float),
            eta=eta,
            eta_names=tuple(str(n) for n in ro.r("names(rpm_vc_fit$eta)")),
            vcov_eta=np.asarray(ro.r("rpm_vc_fit$vcov.eta"), dtype=float),
            gamma=gamma,
            vcov_gamma=np.asarray(ro.r("rpm_vc_fit$vcov.gamma"), dtype=float),
            sigma2=float(np.asarray(ro.r("rpm_vc_fit$sigma2"), dtype=float).ravel()[0]),
            Sigma=np.asarray(ro.r("rpm_vc_fit$Sigma"), dtype=float),
            scales=_opt_arr(ro, "rpm_vc_fit$scales"),  # NULL for method="S"
            min=float(np.asarray(ro.r("rpm_vc_fit$min"), dtype=float).ravel()[0]),
            iterations=int(np.asarray(ro.r("rpm_vc_fit$iterations")).ravel()[0]),
            method=method,
            _r_fit=_fetch_raw("rpm_vc_fit"),
        )
    finally:
        if pushed:
            names = ", ".join(f"'{n}'" for n in pushed)
            ro.r(f"for (v in c({names})) if (exists(v)) rm(list=v)")

    return result


def _fetch_raw(r_name: str):
    """Return a global R object WITHOUT numpy/pandas conversion (for ``.to_r()``)."""
    from rpy2.robjects import conversion, default_converter, r as _rr

    with conversion.localconverter(default_converter):
        return _rr(r_name)
