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

import contextlib
import os
import re
import sys
import threading
import warnings as _warnings
from typing import Any

from robstattm_py._errors import (
    RobStatTMRError,
    RobStatTMSetupError,
    RobStatTMWarning,
)

_init_lock = threading.Lock()
_pkg_cache: dict[str, Any] = {}
_conversion_installed = False
_r_started = False  # flipped True after first successful conversion install
_windows_dll_path_done = False

# Messages from R warnings captured during the most recent guarded R call.
# Populated by ``capture_r_warnings`` / ``r_guard``; readable via
# ``last_r_warnings()``. Thread-local because R is a per-thread singleton here.
_warn_state = threading.local()


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
        print(f"[robstattm_py] R session ready: {ver}", flush=True)


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


def require_r_pkg(name: str) -> None:
    """Ensure an R package is installed *without attaching it* to the search path.

    Unlike :func:`r_pkg` (which ``importr``-attaches the package and, with it, any
    ``Depends:`` packages — e.g. loading ``robustvarComp``/``robcbi`` would attach
    ``robustbase``, whose ``BYlogreg``/``Mscale``/… then **mask** RobStatTM's own
    versions for unqualified R calls), this only loads the namespace. Callers must
    therefore use namespace-qualified ``pkg::fn`` calls (the external wrappers do).

    Raises
    ------
    RobStatTMSetupError
        If the package is not installed.
    """
    ro = r()
    try:
        # `requireNamespace` returns *invisibly*; wrap in isTRUE() to force a
        # visible logical that rpy2 surfaces (otherwise it comes back as None).
        ok = bool(ro.r(f"isTRUE(requireNamespace('{name}', quietly=TRUE))")[0])
    except Exception as e:  # pragma: no cover - rare R-startup failure
        raise RobStatTMSetupError(f"Failed to query R package '{name}': {e}") from e
    if not ok:
        raise RobStatTMSetupError(
            f"R package '{name}' is not installed. "
            f"Run in R:  install.packages('{name}')",
            missing=[name],
        )


# ---------------------------------------------------------------------------
# R warning capture
# ---------------------------------------------------------------------------
#
# rpy2 routes all R console output (including warnings) through the module-level
# callback ``rpy2.rinterface_lib.callbacks.consolewrite_warnerror``. By default
# that callback just forwards the text to a Python ``logger.warning`` — and,
# worse, R *defers* warnings under the default ``options(warn = 0)`` so all the
# user ever sees is R's opaque summary line ("There were 50 or more warnings").
#
# We fix both problems inside :func:`capture_r_warnings`:
#   1. set ``options(warn = 1)`` so R emits each warning immediately (killing the
#      deferred "50 warnings" summary), and
#   2. temporarily swap in a buffering callback that collects the console
#      fragments, which we then parse into individual messages.
#
# The callback layer is below rpy2's Python API, so this covers *every* R call
# path uniformly — both the :func:`rcall` chokepoint and the many direct
# ``ro.r("...")`` string-evals in ``_s3_methods`` and the external wrappers.

# One warning record may reach the console as several fragments, e.g.
# ``"Warning in f(x) :"`` followed by ``" the message\n"``. This matches the
# leading header so we can split the joined text back into individual records.
_R_WARN_HEADER = re.compile(
    r"Warning(?:s)?(?: messages?)?(?: in [^\n:]*)? ?:\s*", re.IGNORECASE
)


def _parse_r_warning_text(fragments: list[str]) -> list[str]:
    """Turn buffered R console fragments into a list of warning messages."""
    text = "".join(fragments)
    if not text.strip():
        return []
    # Split on each "Warning ... :" header; the text after a header (up to the
    # next header) is the message. Drop the empty piece before the first header.
    pieces = _R_WARN_HEADER.split(text)
    out: list[str] = []
    for piece in pieces:
        msg = re.sub(r"\s+", " ", piece).strip()
        # Ignore R's deferred-summary noise and stray blanks.
        if not msg:
            continue
        if re.fullmatch(r"There were \d+ or more warnings.*", msg):
            continue
        if re.fullmatch(r"There were \d+ warnings.*", msg):
            continue
        out.append(msg)
    return out


@contextlib.contextmanager
def capture_r_warnings(*, emit: bool = True):
    """Capture R-side warnings raised while the block runs.

    Yields a list that is populated with the individual warning messages when
    the block exits. When ``emit`` is ``True`` (the default) each message is
    also re-raised through Python's :mod:`warnings` machinery under the
    :class:`~robstattm_py.RobStatTMWarning` category, so it is visible in a
    console or notebook and can be filtered with :func:`warnings.catch_warnings`.

    The captured list is also stored thread-locally and can be retrieved after
    the fact with :func:`last_r_warnings`.

    Example
    -------
    >>> with capture_r_warnings() as w:      # doctest: +SKIP
    ...     fit = rpm.lmrobM("y ~ x", data=df)
    >>> w                                    # doctest: +SKIP
    ['algorithm did not converge in 50 iterations']
    """
    ro = r()
    from rpy2.rinterface_lib import callbacks

    fragments: list[str] = []
    messages: list[str] = []
    prev_cb = callbacks.consolewrite_warnerror
    try:
        prev_warn = ro.r("getOption('warn')")[0]
    except Exception:  # pragma: no cover - R not fully up
        prev_warn = 0

    def _sink(s: str) -> None:
        fragments.append(str(s))

    callbacks.consolewrite_warnerror = _sink
    try:
        try:
            ro.r("options(warn = 1)")
        except Exception:  # pragma: no cover
            pass
        yield messages
    finally:
        callbacks.consolewrite_warnerror = prev_cb
        try:
            ro.r(f"options(warn = {int(prev_warn)})")
        except Exception:  # pragma: no cover
            pass
        messages[:] = _parse_r_warning_text(fragments)
        _warn_state.last = list(messages)
        if emit:
            for m in messages:
                _warnings.warn(m, RobStatTMWarning, stacklevel=3)


def last_r_warnings() -> list[str]:
    """Return the R warning messages from the most recent guarded R call.

    Returns an empty list if no R call has run yet (on this thread) or if the
    last call produced no warnings. Every wrapper call (fits *and* result
    methods such as ``.summary()`` / ``.predict()``) refreshes this list.
    """
    return list(getattr(_warn_state, "last", []))


@contextlib.contextmanager
def r_guard(*, hint: str | None = None, emit_warnings: bool = True):
    """Context manager that captures R warnings *and* translates R errors.

    Wraps a block of R calls so that
      * warnings are collected/emitted via :func:`capture_r_warnings`, and
      * any rpy2 ``RRuntimeError`` is converted to :class:`RobStatTMRError`
        (with R's ``geterrmessage()`` attached), matching the behaviour that
        :func:`rcall` has always provided for fits — now available to the
        direct-``ro.r()`` code paths too.
    """
    from rpy2.rinterface_lib.embedded import RRuntimeError

    with capture_r_warnings(emit=emit_warnings):
        try:
            yield
        except RRuntimeError as e:
            tb = None
            try:
                tb_obj = r().r("paste(geterrmessage())")
                tb = str(tb_obj[0]) if len(tb_obj) else None
            except Exception:  # pragma: no cover
                tb = None
            raise RobStatTMRError(str(e), r_traceback=tb, hint=hint) from e


def rcall(rfun: Any, *args: Any, _hint: str | None = None, **kwargs: Any) -> Any:
    """Call an R function, translating rpy2 errors into RobStatTMRError.

    R warnings raised during the call are captured and surfaced as
    :class:`~robstattm_py.RobStatTMWarning` (see :func:`capture_r_warnings`);
    the message list is also available afterwards via :func:`last_r_warnings`.

    The keyword ``_hint`` is consumed by this wrapper (not passed to R).
    Any other kwarg ending in ``_`` has the trailing underscore stripped
    (escape hatch for Python-reserved-name R kwargs, e.g. ``class_``).
    """
    clean_kwargs = {(k[:-1] if k.endswith("_") else k): v for k, v in kwargs.items()}
    with r_guard(hint=_hint):
        return rfun(*args, **clean_kwargs)


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
