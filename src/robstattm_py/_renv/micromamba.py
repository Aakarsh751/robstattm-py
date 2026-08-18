"""Acquire the micromamba launcher used to build the private R environment.

micromamba is a single statically-linked binary with no installer and no
dependencies, which is why it is the right tool here: provisioning R must work
on a machine that has neither R nor conda, without asking the user to install a
package manager first.

Everything about this module is written on the assumption that the download can
and will go wrong, corporate TLS interception, captive portals, antivirus
quarantine, and half-written files on a full disk are all routine. Each failure
mode gets a specific message rather than a stack trace.

**Maintenance:** to bump the pin, run ``python dev/_refresh_micromamba_pin.py``,
which reads the digests straight from the GitHub release API and rewrites the
table below. ``tests/renv/test_micromamba.py`` asserts that every supported
platform has an entry, so a partial bump fails the suite rather than shipping.
"""
from __future__ import annotations

import hashlib
import os
import ssl
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from robstattm_py._renv import paths
from robstattm_py._renv.errors import (
    EXIT_DISK,
    EXIT_NETWORK,
    RenvError,
)
from robstattm_py._renv.probe import SUPPORTED_SUBDIRS, Probe

#: Pinned micromamba release. Bumping this requires refreshing every digest.
MICROMAMBA_VERSION = "2.9.0-0"

#: SHA-256 of the raw binary for each supported platform, taken from the
#: GitHub release API for :data:`MICROMAMBA_VERSION`.
MICROMAMBA_SHA256: dict[str, str] = {
    "linux-64": "366cd9cd8be14df1ab8ed50352a82111082a36686b2d389fdb79a92c3fafb3e3",
    "linux-aarch64": "9f93b974adcb4d166996af969b6cd371287d1a3e52733704727884d9b74cb7a7",
    "linux-ppc64le": "af28181e62239dcc94ae23eefac3dce24b3d7b17a769810cbee99b183333f9a3",
    "osx-64": "1e71054bb3ac9a076e21f7ec48acfef536f9b3f1408f371a942784bf5ef83d8a",
    "osx-arm64": "ec2a072f028e1a7cf20f3e2e74d5a8127cf5a5f27636375b5359811565f4e5be",
    "win-64": "a6d804394b2418991c4e29562853eaace2f2ce9d9da661a98e74e02e8dbb44b0",
}

_RELEASE_BASE = "https://github.com/mamba-org/micromamba-releases/releases/download"

_CHUNK = 64 * 1024


class NetworkError(RenvError):
    """A download could not be completed."""

    code = "E_NETWORK"
    exit_code = EXIT_NETWORK
    default_remedy = (
        "Check your internet connection. Behind a corporate proxy, set HTTPS_PROXY "
        "(and HTTP_PROXY). If you already have micromamba, pass "
        "--micromamba-path /path/to/micromamba to skip the download."
    )


class TLSError(RenvError):
    """TLS certificate verification failed."""

    code = "E_TLS"
    exit_code = EXIT_NETWORK
    default_remedy = (
        "This usually means a corporate proxy is inspecting HTTPS traffic. Point "
        "SSL_CERT_FILE at your organisation's CA bundle, or re-run with --insecure "
        "to skip verification (only on a network you trust)."
    )


class ChecksumError(RenvError):
    """A download did not match its expected digest."""

    code = "E_CHECKSUM"
    exit_code = EXIT_NETWORK
    default_remedy = (
        "The download was corrupted or intercepted - a captive portal returning an "
        "HTML login page is the usual cause. Try again on a different network, or "
        "pass --micromamba-path with a binary you trust."
    )


class DownloadPermissionError(RenvError):
    """The launcher could not be written or executed."""

    code = "E_AV_BLOCKED"
    exit_code = EXIT_DISK
    default_remedy = (
        "Antivirus software may have quarantined the download. Allow the "
        "robstattm-py directory (on Windows: "
        "Add-MpPreference -ExclusionPath '<dir>' in an elevated PowerShell), or set "
        "ROBSTATTM_HOME to a directory that is excluded from scanning."
    )


class UnsupportedPlatformError(RenvError):
    """conda-forge has no build for this platform."""

    code = "E_UNSUPPORTED_PLATFORM"
    exit_code = EXIT_NETWORK
    default_remedy = (
        "Install R yourself from https://cran.r-project.org/ and robstattm-py will "
        "find it automatically."
    )


def micromamba_url(subdir: str) -> str:
    """Return the download URL for a platform's micromamba binary.

    Uses the GitHub release asset directly rather than the ``micro.mamba.pm``
    redirector: release assets are immutable, and the raw binary needs no
    archive extraction step that could itself fail.
    """
    if subdir not in MICROMAMBA_SHA256:
        raise UnsupportedPlatformError(
            f"No micromamba build is pinned for platform {subdir!r}.",
            detail="Supported: " + ", ".join(sorted(MICROMAMBA_SHA256)),
        )
    suffix = ".exe" if subdir.startswith("win") else ""
    return f"{_RELEASE_BASE}/{MICROMAMBA_VERSION}/micromamba-{subdir}{suffix}"


def _sha256_of(path: Path) -> str:
    """Return the hex SHA-256 of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(_CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def _open_url(url: str, *, timeout: int, insecure: bool):
    """Open a URL, translating transport failures into our error types.

    Uses :mod:`urllib` rather than adding a ``requests`` dependency: urllib
    already honours ``HTTPS_PROXY``/``NO_PROXY`` and ``SSL_CERT_FILE``, which is
    everything a corporate network needs.
    """
    context = ssl._create_unverified_context() if insecure else None  # noqa: S323
    try:
        return urllib.request.urlopen(url, timeout=timeout, context=context)  # noqa: S310
    except urllib.error.HTTPError as exc:
        raise NetworkError(
            f"Download failed with HTTP {exc.code} for {url}.",
            detail=f"Server said: {exc.reason}",
        ) from exc
    except ssl.SSLCertVerificationError as exc:
        raise TLSError(
            f"TLS certificate verification failed for {url}.",
            detail=str(exc),
        ) from exc
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, ssl.SSLCertVerificationError):
            raise TLSError(
                f"TLS certificate verification failed for {url}.", detail=str(reason)
            ) from exc
        proxies = {
            k: v
            for k, v in os.environ.items()
            if k.lower() in {"http_proxy", "https_proxy", "no_proxy"}
        }
        raise NetworkError(
            f"Could not reach {url}.",
            detail=f"Reason: {reason}\nProxy settings in effect: {proxies or 'none'}",
        ) from exc
    except OSError as exc:
        raise NetworkError(f"Could not reach {url}.", detail=str(exc)) from exc


def download(
    url: str,
    destination: Path,
    *,
    expected_sha256: str | None = None,
    timeout: int = 180,
    insecure: bool = False,
    progress: Callable[[int, int | None], None] | None = None,
) -> Path:
    """Download ``url`` to ``destination``, atomically and verified.

    Writes to a temporary sibling and renames on success, so an interrupted
    download can never leave a truncated binary that looks installed.
    """
    paths.ensure_dir(destination.parent)
    partial = destination.with_name(f".{destination.name}.{os.getpid()}.part")

    digest = hashlib.sha256()
    downloaded = 0
    try:
        with _open_url(url, timeout=timeout, insecure=insecure) as response:
            total_header = response.headers.get("Content-Length")
            total = int(total_header) if total_header else None
            with partial.open("wb") as out:
                while True:
                    block = response.read(_CHUNK)
                    if not block:
                        break
                    out.write(block)
                    digest.update(block)
                    downloaded += len(block)
                    if progress is not None:
                        progress(downloaded, total)
                out.flush()
                os.fsync(out.fileno())
    except PermissionError as exc:
        partial.unlink(missing_ok=True)
        raise DownloadPermissionError(
            f"Could not write to {destination.parent}.", detail=str(exc)
        ) from exc
    except OSError as exc:
        partial.unlink(missing_ok=True)
        if getattr(exc, "errno", None) == 28:  # ENOSPC
            raise DownloadPermissionError(
                f"Ran out of disk space while writing {destination}.", detail=str(exc)
            ) from exc
        raise
    except BaseException:
        partial.unlink(missing_ok=True)
        raise

    actual = digest.hexdigest()
    if expected_sha256 and actual != expected_sha256:
        partial.unlink(missing_ok=True)
        raise ChecksumError(
            "Downloaded file does not match its expected checksum.",
            detail=(
                f"url:      {url}\n"
                f"expected: {expected_sha256}\n"
                f"got:      {actual}\n"
                f"size:     {downloaded} bytes"
            ),
        )

    try:
        os.replace(partial, destination)
    except OSError as exc:
        partial.unlink(missing_ok=True)
        raise DownloadPermissionError(
            f"Could not install the download at {destination}.", detail=str(exc)
        ) from exc
    return destination


def ensure_micromamba(
    *,
    probe: Probe | None = None,
    verify: bool = True,
    timeout: int = 180,
    insecure: bool = False,
    override: Path | None = None,
    progress: Callable[[int, int | None], None] | None = None,
) -> Path:
    """Return a usable micromamba binary, downloading it if necessary.

    Parameters
    ----------
    override : Path, optional
        Use this binary instead of downloading. For air-gapped machines and for
        sites whose policy forbids downloading executables.
    verify : bool, optional
        Check the SHA-256 against the pinned value.

    Returns
    -------
    Path
        An existing, executable micromamba.
    """
    probe = probe or Probe.current()

    if override is not None:
        candidate = Path(override).expanduser()
        if not candidate.is_file():
            raise DownloadPermissionError(f"No micromamba binary at {candidate}.")
        return candidate

    subdir = probe.subdir
    if subdir not in SUPPORTED_SUBDIRS or subdir not in MICROMAMBA_SHA256:
        raise UnsupportedPlatformError(
            f"Cannot provision R on this platform ({probe.system}/{probe.machine}).",
            detail="Supported platforms: " + ", ".join(sorted(MICROMAMBA_SHA256)),
        )

    target = paths.micromamba_exe(probe)
    expected = MICROMAMBA_SHA256[subdir] if verify else None

    if target.is_file():
        if not verify or _sha256_of(target) == expected:
            return _make_executable(target)
        # Wrong version or a corrupted file: replace it rather than fail.
        target.unlink(missing_ok=True)

    download(
        micromamba_url(subdir),
        target,
        expected_sha256=expected,
        timeout=timeout,
        insecure=insecure,
        progress=progress,
    )
    return _make_executable(target)


def _make_executable(path: Path) -> Path:
    """Give the binary the execute bit and confirm it survived.

    The post-write ``stat`` is not paranoia: antivirus on Windows commonly
    deletes a freshly written executable *after* the write succeeds, which would
    otherwise surface much later as a confusing "file not found".
    """
    try:
        if os.name != "nt":
            path.chmod(path.stat().st_mode | 0o755)
        if not path.is_file():
            raise DownloadPermissionError(
                f"{path} disappeared immediately after being written.",
                detail="This is the signature of an antivirus product quarantining it.",
            )
    except PermissionError as exc:
        raise DownloadPermissionError(
            f"Could not make {path} executable.", detail=str(exc)
        ) from exc
    return path


__all__ = [
    "MICROMAMBA_SHA256",
    "MICROMAMBA_VERSION",
    "ChecksumError",
    "DownloadPermissionError",
    "NetworkError",
    "TLSError",
    "UnsupportedPlatformError",
    "download",
    "ensure_micromamba",
    "micromamba_url",
]
