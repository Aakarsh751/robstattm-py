"""The single rpy2 bridge.

Per ``decisions.md`` D-004, D-009, D-010:

* Conversion context is set once at package import (default + numpy2ri +
  pandas2ri); this survives Jupyter async cells.
* ``importr("RobStatTM")`` is deferred until first wrapper call via the
  ``r_pkg("RobStatTM")`` accessor.
* No threading — R is a singleton.

Public surface kept small on purpose; wrappers should not import any other
rpy2 names directly.
"""
from __future__ import annotations

import os
import sys
import threading
from typing import Any

from robstatm_py._errors import RobStatTMRError, RobStatTMSetupError

_init_lock = threading.Lock()
_pkg_cache: dict[str, Any] = {}
_conversion_installed = False
_r_started = False  # flipped True after first successful conversion install
_windows_dll_path_done = False


def _ensure_windows_r_dll_path() -> None:
    """Prepend R's ``bin/x64`` to the DLL search path on Windows.

    When Python embeds R via rpy2, Windows does not inherit the same DLL
    search path as a standalone ``Rscript.exe`` process.  Without this,
    loading base packages such as ``stats`` fails with::

        LoadLibrary failure: The specified module could not be found.

    Must run before rpy2 initialises the embedded R interpreter.
    """
    global _windows_dll_path_done
    if _windows_dll_path_done or sys.platform != "win32":
        return
    _windows_dll_path_done = True

    r_home = os.environ.get("R_HOME")
    if not r_home:
        try:
            from rpy2.situation import get_r_home

            r_home = get_r_home()
        except Exception:
            return
    if not r_home:
        return

    r_bin = os.path.join(os.path.normpath(r_home), "bin", "x64")
    if not os.path.isdir(r_bin):
        return

    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(r_bin)
        except OSError:
            pass

    path = os.environ.get("PATH", "")
    if r_bin.lower() not in path.lower():
        os.environ["PATH"] = r_bin + os.pathsep + path


def r_started() -> bool:
    """Return ``True`` once the rpy2 conversion context is installed.

    Used by ``rpm.r_started()`` (UI doc §11). Cheap and side-effect-free —
    does NOT trigger R startup.
    """
    return _r_started


def _install_conversion() -> None:
    """Install the default + numpy + pandas conversion context once.

    Note: ``set_conversion`` is *process-global* — it changes the active rpy2
    converter for the whole interpreter, not just this package. This is a
    deliberate trade-off (per decisions.md D-004/D-009/D-010) so the context
    survives Jupyter async cells; the cost is that another rpy2-using library in
    the same process shares it. We intentionally do not push/pop a local
    converter per call.
    """
    global _conversion_installed, _r_started
    if _conversion_installed:
        return
    _ensure_windows_r_dll_path()
    try:
        from rpy2.robjects import default_converter, numpy2ri, pandas2ri
        from rpy2.robjects.conversion import set_conversion
    except ImportError as e:  # pragma: no cover - import-time failure
        raise RobStatTMSetupError(
            "rpy2 is not installed. Install with `pip install rpy2>=3.6`."
        ) from e
    cv = default_converter + numpy2ri.converter + pandas2ri.converter
    set_conversion(cv)
    _conversion_installed = True
    _r_started = True
    # UI doc §11: print a one-line startup message when RPM_VERBOSE=1.
    import os as _os
    if _os.environ.get("RPM_VERBOSE", "") == "1":
        try:
            import rpy2.robjects as _ro
            ver = str(_ro.r("R.version.string")[0])
        except Exception:
            ver = "(version unknown)"
        print(f"[robstatm_py] R session ready: {ver}", flush=True)


def r() -> Any:
    """Return the rpy2 ``robjects`` module, initialising conversion if needed."""
    _install_conversion()
    import rpy2.robjects as ro  # local import to keep package import cheap

    return ro


def r_pkg(name: str) -> Any:
    """Return the importr handle for an R package, caching after first call.

    Raises
    ------
    RobStatTMSetupError
        If the R package is not installed.
    """
    with _init_lock:
        if name in _pkg_cache:
            return _pkg_cache[name]

        _install_conversion()
        from rpy2.robjects.packages import PackageNotInstalledError, importr

        try:
            pkg = importr(name)
        except PackageNotInstalledError as e:
            raise RobStatTMSetupError(
                f"R package '{name}' is not installed. "
                f"Run in R:  install.packages('{name}')",
                missing=[name],
            ) from e
        except Exception as e:  # pragma: no cover - rare R-startup failure
            raise RobStatTMSetupError(
                f"Failed to load R package '{name}': {e}"
            ) from e

        _pkg_cache[name] = pkg
        return pkg


def rcall(rfun: Any, *args: Any, _hint: str | None = None, **kwargs: Any) -> Any:
    """Call an R function, translating rpy2 errors into RobStatTMRError.

    The keyword ``_hint`` is consumed by this wrapper (not passed to R).
    Any other kwarg ending in ``_`` has the trailing underscore stripped
    (escape hatch for Python-reserved-name R kwargs, e.g. ``class_``).
    """
    from rpy2.rinterface_lib.embedded import RRuntimeError

    clean_kwargs = {(k[:-1] if k.endswith("_") else k): v for k, v in kwargs.items()}
    try:
        return rfun(*args, **clean_kwargs)
    except RRuntimeError as e:
        # Try to capture an R-side traceback for the user
        tb = None
        try:
            tb_obj = r().r("paste(geterrmessage())")
            tb = str(tb_obj[0]) if len(tb_obj) else None
        except Exception:  # pragma: no cover
            tb = None
        raise RobStatTMRError(str(e), r_traceback=tb, hint=_hint) from e


def rx2(robj: Any, name: str) -> Any:
    """Return ``robj[[name]]``.

    Works for both raw rpy2 ListVectors (``.rx2``) and converted NamedList /
    dict-like objects (``[name]``). The auto-conversion context can produce
    either; this helper hides that.
    """
    rx2 = getattr(robj, "rx2", None)
    if callable(rx2):
        return rx2(name)
    # NamedList (rpy2.rlike.container) — has .getbyname()
    getbyname = getattr(robj, "getbyname", None)
    if callable(getbyname):
        return getbyname(name)
    # Plain dict / OrdDict fallback
    if hasattr(robj, "__getitem__"):
        try:
            return robj[name]
        except (KeyError, TypeError):
            pass
    raise KeyError(f"field {name!r} not found on {type(robj).__name__}")


def rx2_opt(robj: Any, name: str, default: Any = None) -> Any:
    """Like :func:`rx2` but returns ``default`` when the field is absent.

    Some R fits omit fields depending on the model (e.g. ``lmrobdetMM`` drops
    ``iters.const`` for no-intercept formulas). Use this for genuinely optional
    fields so a missing one yields ``None`` instead of an opaque
    ``ValueError: list.index(x): x not in list``.
    """
    try:
        return rx2(robj, name)
    except (KeyError, ValueError, TypeError):
        return default


def to_py(rval: Any) -> Any:
    """Convert an R object to its native Python form using the active context."""
    from rpy2.robjects import conversion

    with conversion.localconverter(conversion.get_conversion()):
        return conversion.get_conversion().rpy2py(rval)
