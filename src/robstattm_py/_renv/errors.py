"""Error hierarchy and exit-code contract for the R-environment subsystem.

Every failure the ``robstattm-py`` CLI can produce is represented here by a
class carrying three things:

``code``
    A stable ``E_*`` identifier, safe to grep for in logs and to reference from
    the troubleshooting guide.
``exit_code``
    The process exit status the CLI returns for this failure. Documented in
    ``docs/guides/troubleshooting.md`` and asserted by
    ``tests/renv/test_errors.py``.
``remedy``
    A concrete next action for the user. Never ``None``, if we cannot suggest
    anything better than "report a bug", we say that explicitly.

All of these subclass :class:`~robstattm_py.RobStatTMSetupError`, so existing
``except RobStatTMSetupError`` call sites (e.g. in ``_r.py`` and the wrappers)
keep working unchanged.
"""
from __future__ import annotations

from robstattm_py._errors import RobStatTMSetupError

# ---------------------------------------------------------------------------
# Exit-code contract
# ---------------------------------------------------------------------------
#
# Kept as a plain dict rather than an enum so the CLI, the tests and the docs
# can all reference the same table. ``test_errors.py`` asserts that every
# RenvError subclass appears here and that every value is documented.

EXIT_OK = 0
EXIT_INTERNAL = 1
EXIT_USAGE = 2
EXIT_NO_R = 10
EXIT_R_PKG_MISSING = 11
EXIT_ARCH_MISMATCH = 12
EXIT_NETWORK = 13
EXIT_DISK = 14
EXIT_PROVISION = 15
EXIT_ARM64_BUILD = 16
EXIT_LOCKED = 17
EXIT_CONFIRM_REQUIRED = 20

EXIT_CODE_MEANINGS: dict[int, str] = {
    EXIT_OK: "success",
    EXIT_INTERNAL: "unexpected internal error",
    EXIT_USAGE: "command-line usage error",
    EXIT_NO_R: "no usable R installation found",
    EXIT_R_PKG_MISSING: "R found, but required R packages are missing",
    EXIT_ARCH_MISMATCH: "R and Python architectures differ",
    EXIT_NETWORK: "network, proxy, or TLS failure",
    EXIT_DISK: "insufficient disk space or permissions",
    EXIT_PROVISION: "provisioning the private R environment failed",
    EXIT_ARM64_BUILD: "building RobStatTM from source on Apple Silicon failed",
    EXIT_LOCKED: "another robstattm-py setup is already running",
    EXIT_CONFIRM_REQUIRED: "confirmation required but stdin is not a terminal",
}


class RenvError(RobStatTMSetupError):
    """Base class for R-environment discovery and provisioning failures.

    Parameters
    ----------
    message : str
        What went wrong, in one or two sentences.
    remedy : str, optional
        What the user should do about it. Falls back to the class default.
    detail : str, optional
        Supporting evidence, a discovery trace, the tail of a build log, the
        offending path. Printed after the message, never inside it.
    """

    code: str = "E_RENV"
    exit_code: int = EXIT_INTERNAL
    default_remedy: str = (
        "Run `robstattm-py doctor` for a full diagnosis, and include its output "
        "if you report this."
    )

    def __init__(
        self,
        message: str,
        *,
        remedy: str | None = None,
        detail: str | None = None,
        missing: list[str] | None = None,
    ) -> None:
        self.remedy: str = remedy or self.default_remedy
        self.detail: str | None = detail
        self.short_message: str = message

        full = message
        if detail:
            full = f"{full}\n\n{detail}"
        full = f"{full}\n\nWhat to do:\n  {self.remedy}"
        super().__init__(full, missing=missing)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return super().__str__()


# ---------------------------------------------------------------------------
# Discovery failures (Phase 1)
# ---------------------------------------------------------------------------


class NoRFoundError(RenvError):
    """The discovery chain was exhausted without finding a usable R."""

    code = "E_NO_R"
    exit_code = EXIT_NO_R
    default_remedy = (
        "Run `robstattm-py setup` to download a private R (about 400 MB), or "
        "install R yourself and set R_HOME. See "
        "https://aakarsh751.github.io/robstattm-py/guides/troubleshooting.html"
    )


class InvalidRHomeError(RenvError):
    """A specific candidate path is not a usable R home.

    Raised by :func:`robstattm_py._renv.validate.validate_r_home`. During
    discovery this is caught per-candidate and recorded in the trace; it only
    reaches the user when they named the path explicitly (``ROBSTATTM_R_HOME``).
    """

    code = "E_INVALID_R_HOME"
    exit_code = EXIT_NO_R
    default_remedy = (
        "Point ROBSTATTM_R_HOME at the R installation root - the directory that "
        "contains `library/` and `etc/`, e.g. C:\\Program Files\\R\\R-4.5.2 or "
        "/usr/lib/R - not at its `bin` subdirectory."
    )


class RTooOldError(RenvError):
    """A valid R was found but predates the minimum supported version."""

    code = "E_R_TOO_OLD"
    exit_code = EXIT_NO_R
    default_remedy = (
        "Upgrade R to 4.2 or newer, or run `robstattm-py setup` to provision a "
        "supported R alongside it."
    )


class ArchMismatchError(RenvError):
    """R's architecture differs from the running Python's.

    This is fatal *by design*. Handing rpy2 an R shared library built for a
    different architecture does not raise, it crashes the interpreter, so the
    candidate is rejected before rpy2 ever sees it.
    """

    code = "E_ARCH_MISMATCH"
    exit_code = EXIT_ARCH_MISMATCH
    default_remedy = (
        "Install an R matching your Python's architecture, or run "
        "`robstattm-py setup` to provision a matching one automatically."
    )


class RpyAlreadyLoadedError(RenvError):
    """rpy2 was initialised against a different R before we could configure it.

    rpy2 resolves ``R_HOME`` and ``dlopen``s R at *module import* time
    (``rpy2/rinterface_lib/openrlib.py``), so once another library has imported
    ``rpy2.robjects`` the choice of R is fixed for the life of the process.
    """

    code = "E_RPY2_ALREADY_LOADED"
    exit_code = EXIT_INTERNAL
    default_remedy = (
        "Import robstattm_py before rpy2 (or before any library that imports "
        "rpy2), or set ROBSTATTM_R_HOME to the R that rpy2 already loaded."
    )


class RPackagesMissingError(RenvError):
    """R itself works, but required R packages are not installed."""

    code = "E_R_PKG_MISSING"
    exit_code = EXIT_R_PKG_MISSING
    default_remedy = "Run `robstattm-py install-r-packages` to install them."


__all__ = [
    "EXIT_ARCH_MISMATCH",
    "EXIT_ARM64_BUILD",
    "EXIT_CODE_MEANINGS",
    "EXIT_CONFIRM_REQUIRED",
    "EXIT_DISK",
    "EXIT_INTERNAL",
    "EXIT_LOCKED",
    "EXIT_NETWORK",
    "EXIT_NO_R",
    "EXIT_OK",
    "EXIT_PROVISION",
    "EXIT_R_PKG_MISSING",
    "EXIT_USAGE",
    "ArchMismatchError",
    "InvalidRHomeError",
    "NoRFoundError",
    "RPackagesMissingError",
    "RTooOldError",
    "RenvError",
    "RpyAlreadyLoadedError",
]
