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
import re
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

# Messages from R warnings captured during the most recent guarded R call.
# Populated by ``capture_r_warnings`` / ``r_guard``; readable via
# ``last_r_warnings()``. Thread-local because R is a per-thread singleton here.
_warn_state = threading.local()


def _ensure_r_environment() -> Any:
    """Locate, validate and activate an R installation.

    Delegates to :mod:`robstattm_py._renv`, which searches a documented chain of
    locations (``ROBSTATTM_R_HOME``, the private provisioned environment,
    ``R_HOME``, conda prefixes, ``PATH``, the Windows registry, and the
    conventional install roots for each OS), rejects any candidate whose
    architecture does not match this interpreter, and puts R's library
    directories on the search path.

    Must run **before** rpy2 is imported: rpy2 resolves ``R_HOME`` and
    ``dlopen``s R at ``rpy2.rinterface_lib.openrlib`` import time, so the choice
    of R is fixed from that moment on.

    Raises
    ------
    RobStatTMSetupError
        When no usable R is found. The message lists every location that was
        checked and why each was rejected.
    """
    from robstattm_py._renv import ensure_r_environment

    return ensure_r_environment()


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
    info = _ensure_r_environment()
    _harden_rpy2_windows_probe()
    _select_cffi_mode(info)
    try:
        with _quiet_rpy2_probe():
            from rpy2.robjects import default_converter, numpy2ri, pandas2ri
            from rpy2.robjects.conversion import set_conversion
    except ImportError as e:
        raise _rpy2_import_error(e) from e
    cv = default_converter + numpy2ri.converter + pandas2ri.converter
    set_conversion(cv)
    _conversion_installed = True
    _r_started = True
    _ensure_random_seed_exists()
    # UI doc §11: print a one-line startup message when RPM_VERBOSE=1.
    import os as _os
    if _os.environ.get("RPM_VERBOSE", "") == "1":
        try:
            import rpy2.robjects as _ro
            ver = str(_ro.r("R.version.string")[0])
        except Exception:
            ver = "(version unknown)"
        print(f"[robstattm_py] R session ready: {ver}", flush=True)


def _rpy2_is_installed() -> bool:
    """True if rpy2 is importable at all, independently of whether R loads."""
    import importlib.util

    try:
        return importlib.util.find_spec("rpy2") is not None
    except (ImportError, ValueError):  # pragma: no cover - broken install
        return False


def _select_cffi_mode(info: Any, modules: dict | None = None) -> None:
    """Choose rpy2's binding **before** rpy2 is imported, when we know better.

    rpy2 ships two bindings. ``_rinterface_cffi_api`` is compiled against the
    headers of whichever R was present when rpy2 was built; ``_rinterface_cffi_abi``
    resolves symbols at run time and does not care which R it gets. The compiled
    one is a little faster per call and fails outright against a different R.

    ABI is forced in exactly one case: **the R is one we provisioned**, so rpy2 —
    which arrived from a wheel or a base image — was almost certainly not built
    against it. Choosing ABI before rpy2 is imported avoids a failure that cannot
    be recovered from afterwards (rpy2 embeds R as a process-global singleton;
    once an import has attempted to load R the attempt cannot be undone).

    A **system R is deliberately left alone**, and this restraint matters more
    than it looks. It is plausibly the very R rpy2 was built against; on Google
    Colab and Kaggle it *provably* is, because ``pip`` rebuilds rpy2 from source
    against ``/usr/lib/R`` as it installs. A broader rule that forced ABI on those
    hosts was tried and reverted: it broke that working path, because rpy2's
    source build resolves ABI differently than its wheel does and failed at import
    with ``cannot import name 'default_converter' from 'rpy2.robjects' (unknown
    location)``. Do not reintroduce it. The right answer on Colab/Kaggle is to use
    the system R (which this leaves on its matching compiled binding) rather than
    provision a separate one.

    An explicit ``RPY2_CFFI_MODE`` always wins; this only fills in a default.

    ``modules`` overrides the loaded-module table, for tests. The suite has
    long since imported rpy2 by the time these run, so without it every case
    would take the "too late" branch and prove nothing.
    """
    import os as _os
    import sys as _sys

    loaded = _sys.modules if modules is None else modules

    if _os.environ.get("RPY2_CFFI_MODE"):
        return  # the user has decided; do not override
    if "rpy2.rinterface_lib.openrlib" in loaded:
        return  # too late — R is already bound
    if getattr(info, "conda_prefix", None) is None:
        return  # a system R that rpy2 was plausibly built against

    _os.environ["RPY2_CFFI_MODE"] = "ABI"


def _rpy2_import_error(original: ImportError) -> RobStatTMSetupError:
    """Explain an rpy2 import failure without guessing at the cause.

    ``from rpy2.robjects import ...`` both imports a package and starts R, and
    both raise ``ImportError``. This used to report every such failure as "rpy2
    is not installed" — which, on a machine where rpy2 plainly is installed,
    sends the reader to fix something that is not broken and discards the
    message that said what actually was. One Colab report showed ``doctor``
    printing rpy2's version and, a few lines below, advising its installation.
    """
    if not _rpy2_is_installed():
        return RobStatTMSetupError(
            "rpy2 is not installed. Install with `pip install rpy2>=3.6`."
        )

    # rpy2 3.6 is split across three separately-versioned distributions (rpy2,
    # rpy2-rinterface, rpy2-robjects). When their versions drift out of step —
    # the state Google Colab and Kaggle sometimes ship, and which a partial pip
    # upgrade reproduces — `rpy2.robjects` resolves to an empty namespace package
    # with no __file__, and the import fails with "(unknown location)". That is a
    # broken *install*, not a failure to load R; the remedy is entirely different,
    # so it is detected and reported on its own terms rather than as a binding
    # problem.
    msg = str(original)
    if "unknown location" in msg or ("rpy2.robjects" in msg and "cannot import name" in msg):
        return _rpy2_inconsistent_install_error(original)

    import os as _os

    try:
        from robstattm_py._renv import r_home_info

        where = str(r_home_info().path)
    except Exception:  # pragma: no cover - discovery succeeded to reach here
        where = "the R that was found"

    mode = _os.environ.get("RPY2_CFFI_MODE", "(unset — rpy2's compiled default)")
    return RobStatTMSetupError(
        "rpy2 is installed, but it could not load R.\n"
        f"  R:                {where}\n"
        f"  RPY2_CFFI_MODE:   {mode}\n"
        f"  rpy2 reported:    {original}\n\n"
        "The usual cause is rpy2's compiled binding having been built against a "
        "different R than the one above — common wherever rpy2 arrived prebuilt "
        "(Colab, Kaggle, a distro package) and R came from `robstattm-py setup`.\n\n"
        "What to do:\n"
        "  1. Force rpy2's compiler-free binding. It must be set BEFORE Python "
        "starts, or in the very first notebook cell before any import:\n"
        "       export RPY2_CFFI_MODE=ABI\n"
        "       # or:  import os; os.environ['RPY2_CFFI_MODE'] = 'ABI'\n"
        "  2. Or rebuild rpy2 against this R:\n"
        "       pip install --force-reinstall --no-binary rpy2 rpy2\n"
        "  3. Or use the R that rpy2 was built for:\n"
        "       robstattm-py setup --use-system-r\n\n"
        "It cannot be switched after R has been loaded: rpy2 embeds R as a "
        "process-global singleton, so a restart is required."
    )


def _rpy2_components() -> dict[str, str]:
    """Return the installed versions of rpy2's split distributions.

    rpy2 3.6 ships as three separately-versioned packages; reading each version
    is what turns "rpy2.robjects is broken" into the concrete evidence
    ``rpy2 3.6.7 / rpy2-rinterface 3.6.6 / rpy2-robjects 3.6.5``.
    """
    from importlib.metadata import PackageNotFoundError, version

    out: dict[str, str] = {}
    for dist in ("rpy2", "rpy2-rinterface", "rpy2-robjects"):
        try:
            out[dist] = version(dist)
        except PackageNotFoundError:
            out[dist] = "(absent)"
    return out


def _rpy2_inconsistent_install_error(original: ImportError) -> RobStatTMSetupError:
    """Report rpy2's split distributions being at mismatched versions.

    This is the Colab/Kaggle "cannot import name 'default_converter' from
    'rpy2.robjects' (unknown location)" failure. Its cause — mismatched rpy2 /
    rpy2-rinterface / rpy2-robjects versions — and its fix are unrelated to which
    R is loaded or which binding is used, so it gets a message of its own.
    """
    listed = "\n".join(f"    {dist:<16} {ver}" for dist, ver in _rpy2_components().items())
    return RobStatTMSetupError(
        "rpy2 is installed, but its components are at mismatched versions, so "
        "`rpy2.robjects` could not be imported:\n"
        f"{listed}\n"
        f"  rpy2 reported:    {original}\n\n"
        "rpy2 3.6 is split across three separately-versioned packages, and Google "
        "Colab and Kaggle sometimes ship them out of step (a partial `pip` upgrade "
        "does the same). Reinstall a consistent set:\n\n"
        "    pip install --force-reinstall --no-cache-dir rpy2\n\n"
        "then restart the runtime or kernel and run again. rpy2 embeds R as a "
        "process-global singleton, so a restart is required for the new install to "
        "take effect."
    )


def _harden_rpy2_windows_probe() -> None:
    """Work around an rpy2 crash when ``R CMD config`` returns nothing.

    On Windows, importing ``rpy2.rinterface_lib.openrlib`` runs::

        rpy2.situation.get_r_flags(R_HOME, '--ldflags')

    and ``rpy2/situation/__init__.py`` then does an unguarded
    ``output_lst[0].startswith('WARNING')``. ``R CMD`` is a shell script, so on
    an R with no ``sh`` available - exactly the conda-forge R that
    ``robstattm-py setup`` installs - that command produces **no output**, and
    the indexing raises ``IndexError``.

    rpy2 wraps the call in ``except subprocess.CalledProcessError`` only, so the
    ``IndexError`` escapes and ``import rpy2.robjects`` fails outright. The
    failure is intermittent in a way that makes it especially confusing: if no
    other R is on ``PATH`` the command exits non-zero, rpy2 catches
    ``CalledProcessError``, and everything works. It only breaks when the user
    *also* has a normal R installed.

    We convert the ``IndexError`` into the ``CalledProcessError`` rpy2 already
    handles, so its own directory-scanning fallback runs - which is the correct
    behaviour, and the path we have already populated ourselves.

    Idempotent, and a no-op off Windows or if rpy2 is already loaded.
    """
    import sys as _sys

    if _sys.platform != "win32":
        return
    if "rpy2.rinterface_lib.openrlib" in _sys.modules:
        return  # too late to matter; R is already resolved

    try:
        import subprocess as _subprocess

        import rpy2.situation as _situation
    except ImportError:  # pragma: no cover - rpy2 missing is handled elsewhere
        return

    original = getattr(_situation, "get_r_flags", None)
    if original is None or getattr(original, "_robstattm_hardened", False):
        return

    def _get_r_flags(r_home, flags):
        try:
            return original(r_home, flags)
        except IndexError as exc:
            raise _subprocess.CalledProcessError(
                returncode=1, cmd=f"R CMD config {flags}", output=""
            ) from exc

    _get_r_flags._robstattm_hardened = True  # type: ignore[attr-defined]
    _situation.get_r_flags = _get_r_flags


#: Output rpy2's ``R CMD config --ldflags`` start-up probe produces on an R that
#: has no shell or build toolchain - i.e. the conda-forge R that
#: ``robstattm-py setup`` installs. rpy2 discards the result and falls back to
#: scanning directories, so none of this indicates a problem.
#:
#: Kept deliberately specific to that probe. Anything else written to stderr is
#: passed straight through, so a real error can never be swallowed.
_PROBE_NOISE = (
    # cmd.exe, when `sh` is absent entirely
    "is not recognized as an internal or external command",
    "operable program or batch file",
    # R's own config.sh, when a shell exists but the build tools do not
    "bin/config.sh: line",
    "make: command not found",
    "was not built as a library",
)


@contextlib.contextmanager
def _quiet_rpy2_probe():
    """Swallow one specific, harmless stderr message from rpy2's start-up.

    On Windows, importing ``rpy2.rinterface_lib.openrlib`` runs
    ``R CMD config --ldflags`` to locate R's libraries. ``R CMD`` is a shell
    script, so on an R with no ``sh`` on ``PATH`` - which is the case for the
    conda-forge R that ``robstattm-py setup`` installs - the command prints::

        'sh' is not recognized as an internal or external command

    rpy2 catches the resulting error and falls back to its own directory scan,
    so nothing is actually wrong. But the message is written by ``cmd.exe``
    straight to the process's stderr, and the first thing a new user sees
    should not look like a failure.

    The redirection is at the file-descriptor level because the text comes from
    a child process, not from Python. Everything captured is inspected and
    anything unrecognised is re-emitted, so a real error can never be hidden.
    """
    import sys as _sys

    if _sys.platform != "win32":
        yield
        return

    import os as _os
    import tempfile

    try:
        stderr_fd = _sys.stderr.fileno()
    except (AttributeError, OSError, ValueError):
        # Captured or replaced stderr (pytest, notebooks): nothing to redirect.
        yield
        return

    saved_fd = _os.dup(stderr_fd)
    with tempfile.TemporaryFile(mode="w+b") as sink:
        try:
            _os.dup2(sink.fileno(), stderr_fd)
            yield
        finally:
            _os.dup2(saved_fd, stderr_fd)
            _os.close(saved_fd)
            sink.seek(0)
            captured = sink.read().decode("utf-8", errors="replace")

    for line in captured.splitlines():
        if line.strip() and not any(marker in line for marker in _PROBE_NOISE):
            print(line, file=_sys.stderr)


def _ensure_random_seed_exists() -> None:
    """Force R's RNG to initialise so ``.Random.seed`` exists in globalenv.

    R does not create ``.Random.seed`` until the RNG is first used. Most code
    accounts for that, but RobStatTM's ``KurtSDNew``/``initPP`` reads it
    unconditionally to save and restore RNG state::

        oldSeed <- get(".Random.seed", mode="numeric", envir=globalenv())

    (``R/KurtSDNew.R:42``; compare ``R/lmrob.MM.R:690``, which correctly guards
    the same operation with ``exists()``.) Since ``covRob`` and
    ``covRobRocke`` route through it (``R/Multirobu.R:123,359``), calling
    ``cov_rob`` as the *first* action in a fresh session fails with::

        object '.Random.seed' of mode 'numeric' was not found

    Interactive R users rarely hit this because something has usually consumed a
    random number already; an embedded session started by rpy2 is pristine.

    ``set.seed(NULL)`` re-initialises the generator from the clock and process
    ID, so ``.Random.seed`` exists without pinning a fixed value — results stay
    random, and a later :func:`robstattm_py.set_seed` still fully determines
    them.
    """
    try:
        import rpy2.robjects as ro

        ro.r('if (!exists(".Random.seed", envir = globalenv())) set.seed(NULL)')
    except Exception:  # pragma: no cover - never block startup over this
        pass


def r() -> Any:
    """Return the rpy2 ``robjects`` module, initialising conversion if needed."""
    _install_conversion()
    import rpy2.robjects as ro  # local import to keep package import cheap

    return ro


def _install_hint(name: str) -> str:
    """Return the right way to install an R package for *this* setup.

    A user whose R was provisioned by ``robstattm-py setup`` has no R console to
    type ``install.packages`` into, so the historical advice was a dead end for
    exactly the people least equipped to work around it.
    """
    try:
        from robstattm_py._renv import r_home_info
        from robstattm_py._renv.report import install_hint

        return "  " + install_hint([name], r_home_info()).replace("\n", "\n  ")
    except Exception:  # pragma: no cover - never let a hint break the real error
        return f"  Run: robstattm-py install-r-packages {name}"


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
                f"R package '{name}' is not installed.\n{_install_hint(name)}",
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
            f"R package '{name}' is not installed.\n{_install_hint(name)}",
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
