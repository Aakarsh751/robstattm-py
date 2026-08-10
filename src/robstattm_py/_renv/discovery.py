"""Find a usable R installation, and record why every rejected one was rejected.

The chain below is ordered from "the user told us explicitly" down to "we
guessed from a well-known location". The first candidate that both validates
and matches the interpreter's architecture wins.

Two design points are worth stating, because both come from real failures:

**Every rejection is recorded, not swallowed.** ``discover`` returns a full
trace alongside the winner. When no R is found, that trace *is* the error
message — "searched 9 locations, here is what was wrong with each" is
actionable, whereas "R not found" is not.

**A broken R never stops the search.** rpy2 consults the Windows registry only
when its ``R RHOME`` subprocess *raises*
(``rpy2/situation/__init__.py``); a stale ``R.bat`` on ``PATH`` that exits 0
with garbage therefore hides a perfectly good registered R install. We walk the
registry unconditionally and treat a non-validating candidate as one more
rejected row in the trace.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from robstattm_py._renv import paths
from robstattm_py._renv.errors import (
    ArchMismatchError,
    InvalidRHomeError,
    NoRFoundError,
    RTooOldError,
)
from robstattm_py._renv.probe import Probe
from robstattm_py._renv.validate import MIN_R_VERSION, RHomeInfo, validate_r_home

#: Environment variable pinning an exact R installation.
ENV_R_HOME = "ROBSTATTM_R_HOME"

#: Environment variable selecting which rungs are eligible.
ENV_MODE = "ROBSTATTM_R_MODE"

#: Directory names under ``<R_HOME>/bin`` that hold per-architecture binaries.
_ARCH_BIN_DIRS = frozenset({"x64", "i386", "arm64"})


@dataclass(frozen=True, slots=True)
class Candidate:
    """A path to try, tagged with where the idea came from."""

    path: Path
    source: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class CandidateResult:
    """The outcome of validating one candidate."""

    candidate: Candidate
    info: RHomeInfo | None = None
    reason: str | None = None

    @property
    def ok(self) -> bool:
        """True when this candidate validated successfully."""
        return self.info is not None

    def describe(self) -> str:
        """One aligned line for the discovery trace."""
        mark = "OK  " if self.ok else "skip"
        if self.ok and self.info is not None:
            tail = f"R {self.info.version_string} ({self.info.arch})"
        else:
            tail = self.reason or "not found"
        return f"  [{mark}] {self.candidate.source:<22} {self.candidate.path}\n         {tail}"


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """The winning R (if any) plus the full audit trail."""

    info: RHomeInfo | None
    trace: tuple[CandidateResult, ...] = field(default=())
    #: The ``ROBSTATTM_R_MODE`` value in force when this search ran.
    mode: str = "auto"

    @property
    def found(self) -> bool:
        """True when a usable R was found."""
        return self.info is not None

    def render_trace(self) -> str:
        """Return the trace as a human-readable block.

        An empty trace is a real outcome, not an oversight: with
        ``ROBSTATTM_R_MODE=provisioned`` the only eligible location is the
        private environment, so if that does not exist there is nothing to
        report. Saying *why* nothing was checked is far more useful than an
        empty list.
        """
        if not self.trace:
            if self.mode == "provisioned":
                return (
                    "  (none - ROBSTATTM_R_MODE=provisioned restricts the search to\n"
                    "   the private R environment, which has not been created yet)"
                )
            if self.mode == "system":
                return (
                    "  (none - ROBSTATTM_R_MODE=system restricts the search to R\n"
                    "   installations on this machine, and none were found)"
                )
            return "  (no candidate locations were checked)"
        return "\n".join(r.describe() for r in self.trace)

    def raise_if_missing(self) -> RHomeInfo:
        """Return the R info, or raise :class:`NoRFoundError` with the trace attached."""
        if self.info is not None:
            return self.info
        raise NoRFoundError(
            "No usable R installation was found.",
            detail="Locations checked:\n" + self.render_trace(),
        )


# ---------------------------------------------------------------------------
# Candidate generators, in priority order
# ---------------------------------------------------------------------------


def _from_env_override(probe: Probe) -> list[Candidate]:
    raw = probe.environ.get(ENV_R_HOME, "").strip()
    return [Candidate(Path(raw), f"env:{ENV_R_HOME}")] if raw else []


def _from_provisioned(probe: Probe) -> list[Candidate]:
    r_home = paths.provisioned_r_home(probe)
    return [Candidate(r_home, "provisioned", "robstattm-py setup")] if r_home.is_dir() else []


def _from_env_r_home(probe: Probe) -> list[Candidate]:
    raw = probe.environ.get("R_HOME", "").strip()
    return [Candidate(Path(raw), "env:R_HOME")] if raw else []


def _from_conda(probe: Probe) -> list[Candidate]:
    out: list[Candidate] = []
    seen: set[Path] = set()
    conda_prefix = probe.environ.get("CONDA_PREFIX", "").strip()
    if conda_prefix:
        p = Path(conda_prefix) / "lib" / "R"
        seen.add(p)
        out.append(Candidate(p, "conda:CONDA_PREFIX"))
    # A pip install into a conda env that was never `conda activate`d still has
    # sys.prefix pointing at it.
    p = probe.sys_prefix / "lib" / "R"
    if p not in seen:
        out.append(Candidate(p, "conda:sys.prefix"))
    return out


def _r_home_from_executable(exe: Path) -> Path | None:
    """Derive ``R_HOME`` from the path of an ``R`` / ``Rscript`` executable.

    ``<R_HOME>/bin/R``, ``<R_HOME>/bin/x64/R.exe`` and a ``/usr/bin/R`` symlink
    into ``/usr/lib/R/bin/R`` all reduce correctly. Returns ``None`` when the
    layout is unrecognised.
    """
    try:
        resolved = exe.resolve()
    except OSError:  # pragma: no cover - broken symlink
        resolved = exe
    parent = resolved.parent
    if parent.name.lower() in _ARCH_BIN_DIRS:
        parent = parent.parent
    if parent.name.lower() == "bin":
        return parent.parent
    return None


def _from_path(probe: Probe) -> list[Candidate]:
    out: list[Candidate] = []
    seen: set[Path] = set()
    for exe_name in ("R", "Rscript"):
        found = probe.which(exe_name)
        if not found:
            continue
        r_home = _r_home_from_executable(Path(found))
        if r_home is not None and r_home not in seen:
            seen.add(r_home)
            out.append(Candidate(r_home, f"path:{exe_name}", f"from {found}"))
    return out


def _from_windows_registry(probe: Probe) -> list[Candidate]:
    """Read ``InstallPath`` from every registered R, newest version first.

    Covers both ``R-core\\R`` and ``R-core\\R64``, and both hives, because
    per-user installs (the default when a user lacks admin rights) land only in
    ``HKEY_CURRENT_USER``.
    """
    if not probe.is_windows:
        return []

    if probe.registry_installs is not None:
        injected = probe.registry_installs()
        labels = dict(injected)
        ordered = sorted(labels, key=lambda p: _version_key(p.name), reverse=True)
        return [Candidate(p, "winreg", labels[p]) for p in ordered]

    try:
        import winreg
    except ImportError:  # pragma: no cover - non-Windows
        return []

    found: dict[Path, str] = {}
    for hive, hive_name in (
        (winreg.HKEY_CURRENT_USER, "HKCU"),
        (winreg.HKEY_LOCAL_MACHINE, "HKLM"),
    ):
        for sub in (r"Software\R-core\R64", r"Software\R-core\R"):
            try:
                with winreg.OpenKey(hive, sub) as key:
                    for path, version in _read_registry_installs(winreg, key):
                        found.setdefault(path, f"{hive_name}\\{sub} {version}".strip())
            except OSError:
                continue

    ordered = sorted(found, key=lambda p: _version_key(p.name), reverse=True)
    return [Candidate(p, "winreg", found[p]) for p in ordered]


def _read_registry_installs(winreg, key) -> list[tuple[Path, str]]:
    """Yield ``(InstallPath, version)`` for a key and each of its subkeys."""
    out: list[tuple[Path, str]] = []

    def _install_path(k) -> str | None:
        try:
            value, _ = winreg.QueryValueEx(k, "InstallPath")
        except OSError:
            return None
        return value if isinstance(value, str) and value.strip() else None

    top = _install_path(key)
    if top:
        out.append((Path(top), ""))

    index = 0
    while True:
        try:
            name = winreg.EnumKey(key, index)
        except OSError:
            break
        index += 1
        try:
            with winreg.OpenKey(key, name) as subkey:
                value = _install_path(subkey)
                if value:
                    out.append((Path(value), name))
        except OSError:
            continue
    return out


def _version_key(name: str) -> tuple:
    """Sort key extracting a version from a directory or registry key name.

    ``"R-4.5.2"`` sorts above ``"R-4.10"``? No — this uses real version
    ordering, so ``4.10`` correctly sorts above ``4.5``.
    """
    token = name.split("-")[-1] if "-" in name else name
    try:
        from packaging.version import InvalidVersion, Version

        try:
            return (1, Version(token))
        except InvalidVersion:
            pass
    except ImportError:  # pragma: no cover - packaging is a declared dep
        pass
    # Fall back to a numeric tuple so ordering stays sane without packaging.
    nums = tuple(int(p) for p in token.replace("-", ".").split(".") if p.isdigit())
    return (0, nums)


def _injected_roots(probe: Probe, source: str) -> list[Candidate] | None:
    """Return candidates from ``probe.system_roots`` when a test supplied them.

    ``None`` means "no injection; search the real filesystem". An empty tuple is
    meaningful and different: it describes a machine with no R installed, and
    must not fall through to the host's actual install locations.
    """
    if probe.system_roots is None:
        return None
    return [Candidate(p, source) for p in probe.system_roots if p.is_dir()]


def _from_windows_scan(probe: Probe) -> list[Candidate]:
    """Glob the conventional Windows install roots, newest version first."""
    if not probe.is_windows:
        return []
    injected = _injected_roots(probe, "winscan")
    if injected is not None:
        return injected
    roots: list[Path] = []
    for var in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
        value = probe.environ.get(var, "").strip()
        if value:
            roots.append(Path(value) / "R")
    local = probe.environ.get("LOCALAPPDATA", "").strip()
    if local:
        roots.append(Path(local) / "Programs" / "R")
    roots.append(Path("C:/R"))

    hits: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        try:
            entries = [p for p in root.iterdir() if p.is_dir() and p.name.upper().startswith("R-")]
        except OSError:
            continue
        for entry in sorted(entries, key=lambda p: _version_key(p.name), reverse=True):
            if entry not in seen:
                seen.add(entry)
                hits.append(entry)
    return [Candidate(p, "winscan") for p in hits]


def _from_macos(probe: Probe) -> list[Candidate]:
    if not probe.is_macos:
        return []
    injected = _injected_roots(probe, "macframework")
    if injected is not None:
        return injected
    out: list[Candidate] = []
    framework = Path("/Library/Frameworks/R.framework")
    current = framework / "Resources"
    if current.is_dir():
        out.append(Candidate(current, "macframework", "current version"))
    versions = framework / "Versions"
    if versions.is_dir():
        try:
            entries = [p for p in versions.iterdir() if p.is_dir()]
        except OSError:
            entries = []
        for entry in sorted(entries, key=lambda p: _version_key(p.name), reverse=True):
            resources = entry / "Resources"
            if resources.is_dir() and resources != current:
                out.append(Candidate(resources, "macframework", entry.name))
    for brew in (Path("/opt/homebrew/lib/R"), Path("/usr/local/lib/R")):
        if brew.is_dir():
            out.append(Candidate(brew, "macbrew"))
    return out


def _from_linux(probe: Probe) -> list[Candidate]:
    if not probe.is_linux:
        return []
    injected = _injected_roots(probe, "linux")
    if injected is not None:
        return injected
    out: list[Candidate] = []
    for fixed in (Path("/usr/lib/R"), Path("/usr/lib64/R"), Path("/usr/local/lib/R")):
        if fixed.is_dir():
            out.append(Candidate(fixed, "linux"))
    # rig / RStudio / Posit multi-version installs.
    opt = Path("/opt/R")
    if opt.is_dir():
        try:
            entries = [p for p in opt.iterdir() if p.is_dir()]
        except OSError:
            entries = []
        for entry in sorted(entries, key=lambda p: _version_key(p.name), reverse=True):
            lib = entry / "lib" / "R"
            if lib.is_dir():
                out.append(Candidate(lib, "linux", f"/opt/R/{entry.name}"))
    return out


def _from_subprocess(probe: Probe) -> list[Candidate]:
    """Last resort: ask R itself where it lives.

    Only reached when every path-derived guess failed, because spawning a
    process is slow and, on Windows, briefly flashes a console window.
    """
    exe = probe.which("R") or probe.which("Rscript")
    if not exe:
        return []
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            [exe, "RHOME"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    out = (proc.stdout or "").strip().splitlines()
    if proc.returncode != 0 or not out:
        return []
    return [Candidate(Path(out[0].strip()), "subprocess:R RHOME", f"from {exe}")]


# ---------------------------------------------------------------------------
# The chain
# ---------------------------------------------------------------------------

#: ``(kind, generator name)`` in search order.
#:
#: Generators are named rather than referenced directly so they are resolved at
#: call time. That keeps the table honest under monkeypatching — a tuple of
#: function objects would capture the originals at import and silently ignore
#: any later substitution, which makes the chain effectively untestable.
_RUNGS: tuple[tuple[str, str], ...] = (
    ("override", "_from_env_override"),
    ("provisioned", "_from_provisioned"),
    ("system", "_from_env_r_home"),
    ("system", "_from_conda"),
    ("system", "_from_path"),
    ("system", "_from_windows_registry"),
    ("system", "_from_windows_scan"),
    ("system", "_from_macos"),
    ("system", "_from_linux"),
    ("system", "_from_subprocess"),
)


def discover(
    *,
    probe: Probe | None = None,
    mode: str | None = None,
    min_version: tuple[int, int, int] = MIN_R_VERSION,
) -> DiscoveryResult:
    """Search for a usable R installation.

    Parameters
    ----------
    probe : Probe, optional
        Host snapshot. Defaults to the running process. Tests pass a synthetic
        probe to exercise other platforms.
    mode : {"auto", "provisioned", "system"}, optional
        Which rungs are eligible. Defaults to ``ROBSTATTM_R_MODE``, else
        ``"auto"``. ``"provisioned"`` ignores system installs; ``"system"``
        ignores the private environment.
    min_version : tuple, optional
        Minimum acceptable R version.

    Returns
    -------
    DiscoveryResult
        Carries the winner (or ``None``) and the full trace.

    Raises
    ------
    InvalidRHomeError, ArchMismatchError, RTooOldError
        Only when ``ROBSTATTM_R_HOME`` is set and does not validate. An
        explicit instruction that cannot be honoured is an error, never a
        silent fallback — otherwise the user is left wondering why their
        setting had no effect.
    """
    probe = probe or Probe.current()
    mode = (mode or probe.environ.get(ENV_MODE, "") or "auto").strip().lower()
    if mode not in {"auto", "provisioned", "system"}:
        mode = "auto"

    trace: list[CandidateResult] = []
    for kind, generator_name in _RUNGS:
        if kind == "provisioned" and mode == "system":
            continue
        if kind == "system" and mode == "provisioned":
            continue

        generator = globals()[generator_name]
        for candidate in generator(probe):
            try:
                info = validate_r_home(
                    candidate.path,
                    probe=probe,
                    source=candidate.source,
                    min_version=min_version,
                )
            except (InvalidRHomeError, ArchMismatchError, RTooOldError) as exc:
                if kind == "override":
                    # The user named this path explicitly. Do not fall through.
                    raise
                trace.append(CandidateResult(candidate, reason=exc.short_message))
                continue
            trace.append(CandidateResult(candidate, info=info))
            return DiscoveryResult(info=info, trace=tuple(trace), mode=mode)

    return DiscoveryResult(info=None, trace=tuple(trace), mode=mode)


def rpy2_already_loaded_r_home() -> str | None:
    """Return the ``R_HOME`` rpy2 has already bound to, if it has.

    rpy2 resolves ``R_HOME`` and ``dlopen``s R when
    ``rpy2.rinterface_lib.openrlib`` is first imported, so once that has
    happened the choice is fixed for the life of the process. Checking
    :data:`sys.modules` avoids importing it ourselves as a side effect.
    """
    module = sys.modules.get("rpy2.rinterface_lib.openrlib")
    if module is None:
        return None
    value = getattr(module, "R_HOME", None)
    return str(value) if value else None


__all__ = [
    "ENV_MODE",
    "ENV_R_HOME",
    "Candidate",
    "CandidateResult",
    "DiscoveryResult",
    "discover",
    "rpy2_already_loaded_r_home",
]
