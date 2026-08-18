"""Collect a complete picture of the R environment, for humans and for scripts.

One collector, two renderers. ``robstattm-py doctor`` prints the text form;
``--json`` emits the machine form (used by CI to assert that a clean-machine run
really did use the provisioned R rather than stumbling onto a system one).
:func:`robstattm_py.check_setup` renders the same data in its established
layout.

The reason this is a data structure rather than a pile of ``print`` calls is the
:attr:`SetupReport.problems` list: every check that can fail contributes a
``(code, severity, message, remedy)`` record, so the summary at the bottom of
``doctor`` is derived from the checks rather than maintained alongside them.
"""
from __future__ import annotations

import platform
import sys
from dataclasses import dataclass, field
from typing import Any

from robstattm_py._renv.discovery import CandidateResult, DiscoveryResult, discover
from robstattm_py._renv.probe import Probe
from robstattm_py._renv.validate import RHomeInfo

#: R packages the wrappers cannot work without.
CORE_R_PACKAGES = ("RobStatTM", "robustbase", "rrcov", "pyinit")

#: Optional packages behind the pense / GSE / TSGS wrappers.
STRETCH_R_PACKAGES = ("pense", "GSE")

#: Optional packages used only by the example-script reproductions.
OPTIONAL_R_PACKAGES = ("robustarima", "robustvarComp", "robcbi", "WWGbook")

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"


@dataclass(frozen=True, slots=True)
class Problem:
    """One thing that is wrong, and what to do about it."""

    code: str
    severity: str
    message: str
    remedy: str

    @property
    def is_error(self) -> bool:
        """True for problems that make the package unusable."""
        return self.severity == SEVERITY_ERROR


@dataclass(frozen=True, slots=True)
class SetupReport:
    """Everything ``doctor`` knows about this machine."""

    python_version: str
    python_arch: str
    executable: str
    in_venv: bool
    platform_subdir: str
    package_version: str
    rpy2_version: str | None = None
    rpy2_cffi_mode: str | None = None
    rpy2_r_home: str | None = None
    r: RHomeInfo | None = None
    r_version_string: str | None = None
    trace: tuple[CandidateResult, ...] = ()
    r_packages: dict[str, str | None] = field(default_factory=dict)
    problems: tuple[Problem, ...] = ()

    @property
    def ok(self) -> bool:
        """True when nothing is wrong at ``error`` severity."""
        return not any(p.is_error for p in self.problems)

    @property
    def core_missing(self) -> list[str]:
        """Core R packages that are not installed."""
        return [p for p in CORE_R_PACKAGES if not self.r_packages.get(p)]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view."""
        return {
            "ok": self.ok,
            "package_version": self.package_version,
            "python": {
                "version": self.python_version,
                "arch": self.python_arch,
                "executable": self.executable,
                "in_venv": self.in_venv,
                "platform_subdir": self.platform_subdir,
            },
            "rpy2": {
                "version": self.rpy2_version,
                "cffi_mode": self.rpy2_cffi_mode,
                "r_home": self.rpy2_r_home,
            },
            "r": None
            if self.r is None
            else {
                "home": str(self.r.path),
                "version": self.r.version_string,
                "arch": self.r.arch,
                # CI asserts on this: a clean-machine provisioning test that
                # silently found a system R would otherwise pass and prove
                # nothing.
                "source": self.r.source,
                "shared_lib": str(self.r.shared_lib),
                "conda_prefix": None if self.r.conda_prefix is None else str(self.r.conda_prefix),
            },
            "r_version_string": self.r_version_string,
            "r_packages": dict(self.r_packages),
            "discovery_trace": [
                {
                    "source": row.candidate.source,
                    "path": str(row.candidate.path),
                    "ok": row.ok,
                    "reason": row.reason,
                }
                for row in self.trace
            ],
            "problems": [
                {
                    "code": p.code,
                    "severity": p.severity,
                    "message": p.message,
                    "remedy": p.remedy,
                }
                for p in self.problems
            ],
        }


def rpy2_version() -> str | None:
    """Return the installed rpy2 version, or ``None`` if it is not installed.

    Queries installed-package metadata first: rpy2 3.6 removed the long-standing
    ``rpy2.__version__`` attribute, so reading the attribute alone reports
    "unknown" on every current install.
    """
    try:
        import rpy2  # noqa: F401
    except ImportError:
        return None

    try:
        from importlib.metadata import PackageNotFoundError, version

        try:
            return version("rpy2")
        except PackageNotFoundError:  # pragma: no cover - unpackaged checkout
            pass
    except ImportError:  # pragma: no cover - importlib.metadata is stdlib
        pass

    import rpy2 as _rpy2

    return getattr(_rpy2, "__version__", "unknown")


def _rpy2_facts() -> tuple[str | None, str | None, str | None]:
    """Return ``(version, cffi_mode, r_home)`` for the installed rpy2.

    Reads ``sys.modules`` for the binding details rather than importing
    ``openrlib``, importing it would itself load R, which is precisely what a
    diagnostic must not do as a side effect. Call this *after* R has been
    started if you want the binding mode to be populated.
    """
    version = rpy2_version()
    if version is None:
        return None, None, None

    mode: str | None = None
    r_home: str | None = None

    module = sys.modules.get("rpy2.rinterface_lib.openrlib")
    if module is not None:
        mode_obj = getattr(module, "cffi_mode", None)
        mode = getattr(mode_obj, "name", None) or (str(mode_obj) if mode_obj else None)
        value = getattr(module, "R_HOME", None)
        r_home = str(value) if value else None
    return version, mode, r_home


def _r_package_versions(names: tuple[str, ...]) -> dict[str, str | None]:
    """Return ``{package: version or None}`` by asking the running R."""
    from robstattm_py._r import r

    rr = r().r
    out: dict[str, str | None] = {}
    for name in names:
        try:
            value = rr(
                f"tryCatch(as.character(packageVersion('{name}')), "
                "error=function(e) NA_character_)"
            )
            text = value[0] if len(value) else None
            out[name] = None if text is None or text == "NA" else str(text)
        except Exception:
            out[name] = None
    return out


def collect_report(
    *,
    start_r: bool = True,
    probe: Probe | None = None,
    include_optional: bool = True,
) -> SetupReport:
    """Gather the full environment picture.

    Parameters
    ----------
    start_r : bool, optional
        Whether to start R and query installed R packages. ``False`` keeps the
        call fast and side-effect free.
    probe : Probe, optional
        Host snapshot, for tests.
    include_optional : bool, optional
        Also probe the stretch and example-script R packages.

    Returns
    -------
    SetupReport
    """
    from robstattm_py import __version__

    probe = probe or Probe.current()
    problems: list[Problem] = []

    if rpy2_version() is None:
        problems.append(
            Problem(
                code="E_NO_RPY2",
                severity=SEVERITY_ERROR,
                message="rpy2 is not installed.",
                remedy='Run: pip install "rpy2>=3.6"',
            )
        )

    discovery: DiscoveryResult
    try:
        discovery = discover(probe=probe)
    except Exception as exc:  # an explicit ROBSTATTM_R_HOME that does not validate
        discovery = DiscoveryResult(info=None, trace=())
        problems.append(
            Problem(
                code=getattr(exc, "code", "E_RENV"),
                severity=SEVERITY_ERROR,
                message=getattr(exc, "short_message", str(exc)),
                remedy=getattr(exc, "remedy", "Run `robstattm-py doctor` for details."),
            )
        )

    info = discovery.info
    r_version_string: str | None = None
    packages: dict[str, str | None] = {}

    if info is None:
        problems.append(
            Problem(
                code="E_NO_R",
                severity=SEVERITY_ERROR,
                message="No usable R installation was found.",
                remedy=(
                    "Run `robstattm-py setup` to download a private R, or install R "
                    "and set R_HOME."
                ),
            )
        )
    elif start_r:
        names = CORE_R_PACKAGES + (
            STRETCH_R_PACKAGES + OPTIONAL_R_PACKAGES if include_optional else ()
        )
        try:
            from robstattm_py._r import r

            r_version_string = str(r().r("R.version.string")[0])
            packages = _r_package_versions(names)
        except Exception as exc:
            problems.append(
                Problem(
                    code="E_R_START_FAILED",
                    severity=SEVERITY_ERROR,
                    message=f"R was found at {info.path} but could not be started: {exc}",
                    remedy=(
                        "Run `robstattm-py setup` to provision a known-good R, or check "
                        "that the installation is complete."
                    ),
                )
            )
        else:
            problems.extend(_package_problems(packages, info))

    problems.extend(_environment_warnings(probe, info))

    # Read these last: the cffi binding mode only becomes observable once rpy2
    # has actually loaded R, which the block above is what triggers.
    rpy2_ver, rpy2_mode, rpy2_home = _rpy2_facts()

    return SetupReport(
        python_version=platform.python_version(),
        python_arch=probe.arch,
        executable=sys.executable,
        in_venv=sys.prefix != getattr(sys, "base_prefix", sys.prefix),
        platform_subdir=probe.subdir,
        package_version=__version__,
        rpy2_version=rpy2_ver,
        rpy2_cffi_mode=rpy2_mode,
        rpy2_r_home=rpy2_home,
        r=info,
        r_version_string=r_version_string,
        trace=discovery.trace,
        r_packages=packages,
        problems=tuple(problems),
    )


def _package_problems(packages: dict[str, str | None], info: RHomeInfo) -> list[Problem]:
    """Turn missing R packages into problems with an install command that fits."""
    out: list[Problem] = []
    missing_core = [p for p in CORE_R_PACKAGES if not packages.get(p)]
    if missing_core:
        out.append(
            Problem(
                code="E_R_PKG_MISSING",
                severity=SEVERITY_ERROR,
                message="Required R packages are missing: " + ", ".join(missing_core),
                remedy=install_hint(missing_core, info),
            )
        )
    missing_stretch = [p for p in STRETCH_R_PACKAGES if p in packages and not packages.get(p)]
    if missing_stretch:
        out.append(
            Problem(
                code="W_STRETCH_MISSING",
                severity=SEVERITY_WARNING,
                message=(
                    "Optional R packages are missing: "
                    + ", ".join(missing_stretch)
                    + " (only the pense / gse / tsgs wrappers need them)."
                ),
                remedy=install_hint(missing_stretch, info),
            )
        )
    return out


def _environment_warnings(probe: Probe, info: RHomeInfo | None) -> list[Problem]:
    """Non-fatal conditions worth telling the user about."""
    out: list[Problem] = []

    if info is not None and info.is_provisioned and probe.environ.get("CONDA_PREFIX"):
        out.append(
            Problem(
                code="W_TWO_ENVIRONMENTS",
                severity=SEVERITY_WARNING,
                message=(
                    "Using the private R while a conda environment is also active. "
                    "Both put shared libraries on the search path, which can shadow "
                    "each other on Windows."
                ),
                remedy=(
                    "Set ROBSTATTM_R_MODE=system and install RobStatTM into the conda "
                    "environment instead, if you hit library-loading errors."
                ),
            )
        )

    if info is not None and probe.subdir in {"osx-arm64"} and not info.is_provisioned:
        out.append(
            Problem(
                code="W_APPLE_SILICON",
                severity=SEVERITY_WARNING,
                message=(
                    "Apple Silicon: conda-forge has no r-robstattm/r-pyinit build for "
                    "osx-arm64, so `robstattm-py setup` must compile them from source."
                ),
                remedy=(
                    "The R found above is being used instead, which is fine. See the "
                    "platform-support guide for details."
                ),
            )
        )
    return out


def install_hint(packages: list[str], info: RHomeInfo | None) -> str:
    """Return the right way to install R packages for *this* setup.

    A user whose R was provisioned by us has no R console to type into, so the
    long-standing "Run in R: install.packages(...)" advice is actively unhelpful
    for them.
    """
    names = " ".join(packages)
    if info is not None and info.is_provisioned:
        return f"Run: robstattm-py install-r-packages {names}"
    quoted = ", ".join(repr(p) for p in packages)
    return (
        f"Run: robstattm-py install-r-packages {names}\n"
        f"  (or, in an R console:  install.packages(c({quoted})) )"
    )


__all__ = [
    "CORE_R_PACKAGES",
    "OPTIONAL_R_PACKAGES",
    "SEVERITY_ERROR",
    "SEVERITY_WARNING",
    "STRETCH_R_PACKAGES",
    "Problem",
    "SetupReport",
    "collect_report",
    "install_hint",
]
