"""``lmrobM.control`` wrapper — companion to ``lmrobdet.control``.

Wraps ``RobStatTM::lmrobM.control``. Parallel structure to
:class:`LmrobdetControl` but with the smaller key set used by
``lmrobM`` (10 fields instead of 25).

R formals (RobStatTM 1.0.11)::

    lmrobM.control(bb = 0.5, efficiency = 0.99, family = "opt",
                   tuning.chi = NULL, tuning.psi = NULL,
                   max.it = 100, rel.tol = 1e-07,
                   mscale_tol = 1e-06, mscale_maxit = 50,
                   trace.lev = 0)
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, Literal

from robstatm_py._r import r_pkg, rcall

# R names with dots → Python underscores.
_R_KEY_MAP = {
    "tuning_psi": "tuning.psi",
    "tuning_chi": "tuning.chi",
    "max_it": "max.it",
    "rel_tol": "rel.tol",
    "trace_lev": "trace.lev",
    # mscale_tol / mscale_maxit already use underscores in R (yes, R is
    # inconsistent here — these are the exact spellings from the formals).
}


def _py_to_r_key(py_key: str) -> str:
    return _R_KEY_MAP.get(py_key, py_key)


@dataclass(frozen=True, slots=True)
class LmrobMControl:
    """Tuning-parameter container for :func:`lmrob_m`.

    All fields mirror ``RobStatTM::lmrobM.control`` (RobStatTM 1.0.11).
    Note that ``lmrobM`` uses a much smaller control surface than
    ``lmrobdetMM`` because it doesn't run the deterministic-initial /
    refine / pyinit cascade — it's the simpler MM regression core.

    See ``RobStatTM::lmrobM.control`` for parameter meanings.
    """

    bb: float = 0.5
    efficiency: float = 0.99
    family: Literal[
        "opt", "mopt", "bisquare", "huber", "moptv0", "optv0"
    ] = "opt"
    tuning_psi: float | None = None
    tuning_chi: float | None = None
    max_it: int = 100
    rel_tol: float = 1e-7
    mscale_tol: float = 1e-6
    mscale_maxit: int = 50
    trace_lev: int = 0
    _r_list: Any = field(default=None, repr=False, compare=False)


def lmrobm_control(**kwargs: Any) -> LmrobMControl:
    """Build an :class:`LmrobMControl` by passing the same kwargs as R's
    ``lmrobM.control``.

    Unknown kwargs raise ``TypeError``.

    Examples
    --------
    >>> from robstatm_py import lmrobm_control
    >>> ctrl = lmrobm_control(efficiency=0.95, family="bisquare")
    >>> ctrl.efficiency
    0.95
    """
    field_names = {f.name for f in fields(LmrobMControl) if not f.name.startswith("_")}
    bad = set(kwargs) - field_names
    if bad:
        raise TypeError(f"unknown lmrobm_control kwargs: {sorted(bad)}")
    return LmrobMControl(**kwargs)


def _control_m_to_r(ctrl: LmrobMControl):
    """Build the actual R ``lmrobM.control`` named list."""
    pkg = r_pkg("RobStatTM")
    default = LmrobMControl()
    r_kwargs: dict[str, Any] = {}
    for f in fields(LmrobMControl):
        if f.name.startswith("_"):
            continue
        v = getattr(ctrl, f.name)
        d = getattr(default, f.name)
        if v is None:
            continue
        # Always pass the headline knobs through; let R fill internal defaults.
        if v == d and f.name not in {"efficiency", "family", "bb"}:
            continue
        r_kwargs[_py_to_r_key(f.name)] = v
    return rcall(pkg.lmrobM_control, **r_kwargs)
