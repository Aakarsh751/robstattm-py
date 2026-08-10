"""Track what has been provisioned, and stop two setups colliding.

Provisioning is the one operation here that takes minutes, touches hundreds of
megabytes, and can be interrupted halfway. The recovery model is deliberately
simple, because clever partial-repair logic is exactly the kind of code that is
never exercised until it is needed and then turns out to be wrong:

* ``ready`` **and** the recorded spec still matches what we would build today →
  do nothing.
* anything else → delete the environment and rebuild it.

Rebuilds are cheap in practice because the downloaded packages live in
``<root>/pkgs``, *outside* the environment directory, and are never discarded.
A rebuild after a crash re-links from cache in seconds rather than
re-downloading a quarter of a gigabyte.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from dataclasses import fields as dc_fields

from robstattm_py._renv import paths
from robstattm_py._renv.errors import EXIT_LOCKED, RenvError
from robstattm_py._renv.probe import Probe

#: Bumped when the on-disk layout changes in a way older state cannot describe.
SCHEMA_VERSION = 1

#: A lock older than this is assumed to belong to a process that died.
STALE_LOCK_SECONDS = 6 * 60 * 60


class LockedError(RenvError):
    """Another provisioning run holds the lock."""

    code = "E_LOCKED"
    exit_code = EXIT_LOCKED
    default_remedy = (
        "Wait for the other run to finish. If nothing is actually running, "
        "re-run with --force-unlock."
    )


@dataclass(frozen=True, slots=True)
class State:
    """What is currently provisioned, and from which specification."""

    schema: int = SCHEMA_VERSION
    status: str = "absent"  # absent | partial | ready
    spec_hash: str = ""
    r_home: str = ""
    r_version: str = ""
    subdir: str = ""
    micromamba_version: str = ""
    packages: dict[str, str] = field(default_factory=dict)
    updated: str = ""

    @property
    def is_ready(self) -> bool:
        """True when a completed environment is recorded."""
        return self.status == "ready"

    def matches(self, spec_hash: str) -> bool:
        """True when this state was built from ``spec_hash`` and finished."""
        return self.is_ready and self.spec_hash == spec_hash

    # -- persistence -------------------------------------------------------

    @classmethod
    def load(cls, probe: Probe | None = None) -> State:
        """Read the recorded state, or return an empty one.

        Unreadable or future-schema state is treated as "nothing provisioned"
        rather than an error: the worst case is one unnecessary rebuild, versus
        a package that refuses to work because of a corrupted metadata file.
        """
        path = paths.state_file(probe)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        if not isinstance(data, dict) or data.get("schema") != SCHEMA_VERSION:
            return cls()
        known = {f.name for f in dc_fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self, probe: Probe | None = None) -> None:
        """Write the state atomically."""
        path = paths.state_file(probe)
        paths.ensure_dir(path.parent)
        payload = asdict(self)
        payload["updated"] = payload["updated"] or _timestamp()
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(temporary, path)

    def with_status(self, status: str, **changes) -> State:
        """Return a copy with a new status and optional field updates."""
        data = asdict(self)
        data.update(changes)
        data["status"] = status
        data["updated"] = _timestamp()
        return State(**data)


def _timestamp() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def spec_hash(specs: list[str], subdir: str, micromamba_version: str) -> str:
    """Return a stable hash of everything that determines the environment.

    Any change to the package list, the target platform, or the launcher version
    produces a different hash, which is what makes "is the existing environment
    still the one we would build?" a single comparison.
    """
    payload = json.dumps(
        {
            "schema": SCHEMA_VERSION,
            "specs": sorted(specs),
            "subdir": subdir,
            "micromamba": micromamba_version,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class SetupLock:
    """A cross-process lock guarding the provisioning directory.

    Necessary for more than just two concurrent ``setup`` runs: the test suite
    probes for R at collection time, so an ``import robstattm_py`` can land in
    the middle of an environment being rebuilt and see a half-linked R.
    """

    def __init__(self, probe: Probe | None = None, *, force: bool = False) -> None:
        self.path = paths.lock_file(probe)
        self.force = force
        self._held = False

    def __enter__(self) -> SetupLock:
        paths.ensure_dir(self.path.parent)
        if self.path.exists() and not self.force:
            age = time.time() - self.path.stat().st_mtime
            if age < STALE_LOCK_SECONDS:
                raise LockedError(
                    "Another robstattm-py setup is already running.",
                    detail=f"Lock file: {self.path}\nHeld by: {self._holder()}",
                )
        try:
            # O_EXCL makes creation atomic, so two processes racing here cannot
            # both believe they won.
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if not self.force:
                raise LockedError(
                    "Another robstattm-py setup is already running.",
                    detail=f"Lock file: {self.path}\nHeld by: {self._holder()}",
                ) from None
            self.path.unlink(missing_ok=True)
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)

        with os.fdopen(fd, "w") as handle:
            handle.write(f"pid={os.getpid()}\nstarted={_timestamp()}\n")
        self._held = True
        return self

    def __exit__(self, *exc_info) -> None:
        if self._held:
            self.path.unlink(missing_ok=True)
            self._held = False

    def _holder(self) -> str:
        """Describe whoever wrote the lock file, for the error message."""
        try:
            return self.path.read_text(encoding="utf-8").strip().replace("\n", ", ")
        except OSError:  # pragma: no cover - lock vanished between checks
            return "unknown"


def clear_lock(probe: Probe | None = None) -> bool:
    """Remove a stale lock. Returns True if one was present."""
    path = paths.lock_file(probe)
    existed = path.exists()
    path.unlink(missing_ok=True)
    return existed



__all__ = [
    "SCHEMA_VERSION",
    "STALE_LOCK_SECONDS",
    "LockedError",
    "SetupLock",
    "State",
    "clear_lock",
    "spec_hash",
]
