"""Shared pytest fixtures + the strict-tier comparison helper."""
from __future__ import annotations

from typing import Any

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# R availability
# ---------------------------------------------------------------------------


def _r_available() -> tuple[bool, str]:
    try:
        from robstattm_py._r import r_pkg

        r_pkg("RobStatTM")
        return True, ""
    except Exception as e:
        return False, str(e)


_R_OK, _R_ERR = _r_available()


needs_r = pytest.mark.skipif(not _R_OK, reason=f"R / RobStatTM unavailable: {_R_ERR}")


def _r_pkg_available(name: str) -> bool:
    """True if the named external R package is installed.

    Uses ``requireNamespace`` (loads the namespace only) rather than
    ``importr``/``r_pkg`` (which *attaches* the package — and any ``Depends:`` —
    to the R search path). Attaching ``robustarima``/``robustvarComp``/``robcbi``
    would pull in ``robustbase``, whose ``BYlogreg``/``Mscale``/… then mask
    RobStatTM's own versions for unqualified R calls in other tests.
    """
    if not _R_OK:
        return False
    try:
        from robstattm_py._r import r

        return bool(r().r(f"isTRUE(requireNamespace('{name}', quietly=TRUE))")[0])
    except Exception:
        return False


_PENSE_OK = _R_OK and _r_pkg_available("pense")
_GSE_OK = _R_OK and _r_pkg_available("GSE")
_ROBUSTARIMA_OK = _R_OK and _r_pkg_available("robustarima")
_ROBUSTVARCOMP_OK = _R_OK and _r_pkg_available("robustvarComp")
_GLMROB_OK = _R_OK and _r_pkg_available("robustbase")
_ROBCBI_OK = _R_OK and _r_pkg_available("robcbi")


def _r_dataset_available(name: str, package: str) -> bool:
    """True if ``data(name, package=package)`` succeeds (probes WWGbook etc.)."""
    if not _R_OK:
        return False
    try:
        from robstattm_py._r import r

        r().r(f'data({name}, package="{package}")')
        return True
    except Exception:
        return False


_WWGBOOK_OK = _r_dataset_available("autism", "WWGbook")
# breslow.dat lives in the `robust` package, not in robustbase/robcbi — the
# estimator package being present says nothing about the data being present.
_BRESLOW_OK = _r_dataset_available("breslow.dat", "robust")

needs_pense = pytest.mark.skipif(
    not _PENSE_OK, reason="external R package 'pense' not installed"
)
needs_gse = pytest.mark.skipif(
    not _GSE_OK, reason="external R package 'GSE' not installed"
)
needs_robustarima = pytest.mark.skipif(
    not _ROBUSTARIMA_OK, reason="external R package 'robustarima' not installed"
)
needs_robustvarcomp = pytest.mark.skipif(
    not _ROBUSTVARCOMP_OK, reason="external R package 'robustvarComp' not installed"
)
needs_wwgbook = pytest.mark.skipif(
    not _WWGBOOK_OK, reason="R data package 'WWGbook' (autism) not installed"
)
needs_breslow = pytest.mark.skipif(
    not _BRESLOW_OK, reason="R package 'robust' (breslow.dat) not installed"
)
needs_glmrob = pytest.mark.skipif(
    not _GLMROB_OK, reason="external R package 'robustbase' not installed"
)
needs_robcbi = pytest.mark.skipif(
    not _ROBCBI_OK, reason="external R package 'robcbi' not installed"
)


# ---------------------------------------------------------------------------
# Direct-R call helper for tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def R():
    """Return a callable ``R(expression_string)`` that evaluates raw R code."""
    from robstattm_py._r import r

    rr = r().r

    def _R(expr: str):
        return rr(expr)

    return _R


# ---------------------------------------------------------------------------
# Strict-tier comparison helpers
# ---------------------------------------------------------------------------


def _as_native(x):
    """Coerce rpy2 vectors / numpy arrays to native Python comparable forms."""
    if x is None:
        return None
    arr = np.asarray(x)
    if arr.dtype.kind in ("f", "i", "u"):
        if arr.ndim == 0:
            return arr.item()
        return arr
    if arr.size == 1:
        return arr.ravel()[0]
    return arr


def assert_scalar_equal(py: Any, r_val: Any, *, where: str = ""):
    """Strict-tier scalar equality. NaN==NaN treated as equal."""
    py_v = _as_native(py)
    r_v = _as_native(r_val)
    if isinstance(py_v, np.ndarray):
        py_v = py_v.item() if py_v.size == 1 else py_v
    if isinstance(r_v, np.ndarray):
        r_v = r_v.item() if r_v.size == 1 else r_v
    if isinstance(py_v, float) and isinstance(r_v, float):
        if np.isnan(py_v) and np.isnan(r_v):
            return
        assert py_v == r_v, f"{where}: py={py_v!r} r={r_v!r}"
    else:
        assert py_v == r_v, f"{where}: py={py_v!r} r={r_v!r}"


def assert_array_equal(py: Any, r_val: Any, *, where: str = ""):
    """Strict-tier element-wise equality (atol=0, rtol=0)."""
    py_a = np.asarray(_as_native(py))
    r_a = np.asarray(_as_native(r_val))
    np.testing.assert_array_equal(py_a, r_a, err_msg=f"field {where}")


def assert_r_equal_dataclass(py_obj, r_list, field_map: dict[str, str]):
    """Strict-tier field-by-field comparison.

    Parameters
    ----------
    py_obj : dataclass instance
        Python wrapper result.
    r_list : rpy2 ListVector
        R fit object.
    field_map : dict[str, str]
        ``{python_attr: r_name}``.
    """
    for py_attr, r_name in field_map.items():
        py_val = getattr(py_obj, py_attr)
        r_val = r_list.rx2(r_name)
        # Decide scalar vs array based on R length
        if hasattr(r_val, "__len__") and len(r_val) > 1:
            assert_array_equal(py_val, r_val, where=py_attr)
        else:
            assert_scalar_equal(py_val, r_val, where=py_attr)


# ---------------------------------------------------------------------------
# Subprocess helper
# ---------------------------------------------------------------------------


def child_preamble() -> str:
    """Python source that makes ``robstattm_py`` importable in a child process.

    Several tests must run in a genuinely fresh interpreter: verifying that
    importing the package has no side effects, and that the *first* call in a
    pristine R session works. Neither is observable in-process once pytest has
    imported everything.

    The obvious way to give the child our import path — setting ``PYTHONPATH``
    — turned out to be the wrong tool, and took four attempts on CI to
    understand. ``PYTHONPATH`` is consulted while the interpreter is still
    booting, so a bad entry breaks start-up itself: on Python 3.12 it produced

        ImportError: .../lib-dynload/_ctypes...so: undefined symbol:
        _PyErr_SetLocaleString

    before a single line of test code ran. Narrowing which directories were
    passed only changed which failure appeared, because the hazard is *when*
    the paths are applied, not which ones.

    Injecting into ``sys.path`` from inside the child sidesteps it entirely:
    by then the interpreter is fully initialised, its own stdlib resolution has
    already happened, and prepending directories cannot disturb it.

    Returns a source prefix to place before the test's own code.
    """
    import site
    import sysconfig
    from pathlib import Path

    import robstattm_py

    wanted: list[str] = [str(Path(robstattm_py.__file__).resolve().parent.parent)]
    for getter in (site.getsitepackages, site.getusersitepackages):
        try:
            found = getter()
        except Exception:  # pragma: no cover - not available in every layout
            continue
        wanted.extend([found] if isinstance(found, str) else list(found))
    for key in ("purelib", "platlib"):
        path = sysconfig.get_paths().get(key)
        if path:
            wanted.append(path)

    seen: set[str] = set()
    ordered = [p for p in wanted if p and not (p in seen or seen.add(p))]
    return "import sys\nsys.path[:0] = " + repr(ordered) + "\n"


def child_env(**overrides: str) -> dict[str, str]:
    """Return the parent environment with all R-related settings removed."""
    import os

    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("R_", "ROBSTATTM_", "RPY2_", "CONDA", "MAMBA"))
    }
    env.update(overrides)
    return env
