"""``lmrobdet.control`` wrapper.

Wraps ``RobStatTM::lmrobdet.control`` (Maronna et al. 2019 §5). The 25-key R
named list is exposed as both a Python dataclass (``LmrobdetControl``) and a
factory function (``lmrobdet_control``).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Literal

from robstatm_py._r import r, r_pkg, rcall

# Per R's lmrobdet.control formal kwargs (25 keys, RobStatTM 1.0.11).
# A few R names use dots; Python uses underscores. See _R_KEY_MAP below.

_R_KEY_MAP = {
    # python_attr -> R kwarg name
    "tuning_psi": "tuning.psi",
    "tuning_chi": "tuning.chi",
    "compute_rd": "compute.rd",
    "corr_b": "corr.b",
    "split_type": "split.type",
    "max_it": "max.it",
    "refine_tol": "refine.tol",
    "rel_tol": "rel.tol",
    "refine_s_py": "refine.S.py",
    "refine_py": "refine.PY",
    "solve_tol": "solve.tol",
    "trace_lev": "trace.lev",
}


def _py_to_r_key(py_key: str) -> str:
    return _R_KEY_MAP.get(py_key, py_key)


@dataclass(frozen=True, slots=True)
class LmrobdetControl:
    """Tuning-parameter container for ``lmrobdet_mm`` / ``lmrobdet_dcml``.

    All fields mirror ``RobStatTM::lmrobdet.control`` (RobStatTM 1.0.11). The
    R names with dots (``tuning.psi``, ``max.it``, …) become Python underscores
    here; mapping handled by ``_R_KEY_MAP``.

    See ``RobStatTM::lmrobdet.control`` for parameter meanings and defaults.
    """

    bb: float = 0.5
    efficiency: float = 0.95
    family: Literal[
        "mopt", "bisquare", "huber", "opt", "moptv0", "optv0"
    ] = "mopt"
    tuning_psi: float | None = None
    tuning_chi: float | None = None
    compute_rd: bool = False
    corr_b: bool = True
    split_type: str = "f"
    initial: str = "S"
    max_it: int = 100
    refine_tol: float = 1e-7
    rel_tol: float = 1e-7
    # R's ``refine.S.py`` is the *relative convergence tolerance* for the local
    # improvement of the Pena-Yohai candidates (a float, default 1e-7) — NOT an
    # iteration count. Verified against R/lmrobdet.R:464.
    refine_s_py: float = 1e-7
    refine_py: int = 10
    solve_tol: float = 1e-7
    trace_lev: int = 0
    psc_keep: float = 0.5
    resid_keep_method: str = "threshold"
    resid_keep_thresh: float = 2.0
    resid_keep_prop: float = 0.2
    py_maxit: int = 20
    py_eps: float = 1e-5
    mscale_maxit: int = 50
    mscale_tol: float = 1e-6
    mscale_rho_fun: str = "bisquare"
    # Echoed R list — populated only when we round-trip from R; users typically
    # do not set this directly.
    _r_list: Any = field(default=None, repr=False, compare=False)


def lmrobdet_control(**kwargs: Any) -> LmrobdetControl:
    """Build a control object by passing the same kwargs as R's ``lmrobdet.control``.

    Unknown kwargs raise ``TypeError`` — this catches typos that would otherwise
    silently fall through to R defaults.

    Parameters
    ----------
    **kwargs
        Any subset of fields documented on :class:`LmrobdetControl`.

    Returns
    -------
    LmrobdetControl

    Examples
    --------
    >>> from robstatm_py import lmrobdet_control
    >>> ctrl = lmrobdet_control(efficiency=0.85, family="bisquare")
    >>> ctrl.efficiency
    0.85
    """
    field_names = {f.name for f in fields(LmrobdetControl) if not f.name.startswith("_")}
    bad = set(kwargs) - field_names
    if bad:
        raise TypeError(f"unknown lmrobdet_control kwargs: {sorted(bad)}")
    return LmrobdetControl(**kwargs)


def _control_to_r(ctrl: LmrobdetControl):
    """Build the actual R ``lmrobdet.control`` named list by calling R.

    The resulting R list contains all 25 keys with R-side defaults filled in,
    not just the ones the user set explicitly. We therefore call R's
    ``lmrobdet.control`` with the keys the user actually changed; this matches
    direct-R usage exactly.
    """
    pkg = r_pkg("RobStatTM")
    default = LmrobdetControl()  # field defaults
    r_kwargs: dict[str, Any] = {}
    for f in fields(LmrobdetControl):
        if f.name.startswith("_"):
            continue
        v = getattr(ctrl, f.name)
        d = getattr(default, f.name)
        # Skip None (means "use R's default") and skip values equal to our
        # Python default that exactly match R's documented default — for the
        # few non-trivial defaults we pass through to be safe.
        if v is None:
            continue
        if v == d and f.name not in {"efficiency", "family", "bb"}:
            # Allow R to fill the default; only pass through the headline knobs
            # the user is likely to care about plus the headline tuning keys.
            continue
        r_kwargs[_py_to_r_key(f.name)] = v
    return rcall(pkg.lmrobdet_control, **r_kwargs)
