"""``robstattm-py info``, show paths and settings, touching nothing.

Never starts R, never creates a directory, always exits 0. That makes it safe to
run first when something looks wrong, and safe to paste into a bug report.
"""
from __future__ import annotations

import json
import shutil

from robstattm_py._renv import paths
from robstattm_py._renv.errors import EXIT_OK
from robstattm_py._renv.probe import SUPPORTED_SUBDIRS, Probe


def add_parser(subparsers) -> None:
    """Attach the ``info`` subcommand."""
    parser = subparsers.add_parser(
        "info",
        help="show the paths and environment variables robstattm-py uses",
        description=(
            "Print where the private R environment would live, how much disk it "
            "occupies, and every environment variable that changes behaviour. "
            "Starts nothing and creates nothing."
        ),
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.set_defaults(_handler=run)


def _directory_size(path) -> int:
    """Return the total size of a directory tree in bytes, or 0 if absent."""
    if not path.is_dir():
        return 0
    total = 0
    for entry in path.rglob("*"):
        try:
            if entry.is_file():
                total += entry.stat().st_size
        except OSError:  # pragma: no cover - races and permission quirks
            continue
    return total


def _human(size: int) -> str:
    """Format a byte count for humans."""
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"  # pragma: no cover - unreachable


def collect(probe: Probe | None = None) -> dict:
    """Gather the information ``info`` reports."""
    from robstattm_py import __version__

    probe = probe or Probe.current()
    root = paths.root(probe)
    env_prefix = paths.env_prefix(probe)

    free = None
    try:
        target = root if root.exists() else root.parent
        while not target.exists() and target != target.parent:
            target = target.parent
        free = shutil.disk_usage(target).free
    except OSError:  # pragma: no cover - unusual filesystems
        free = None

    return {
        "version": __version__,
        "platform_subdir": probe.subdir,
        "supported_subdirs": list(SUPPORTED_SUBDIRS),
        "paths": {
            "root": str(root),
            "env_prefix": str(env_prefix),
            "provisioned_r_home": str(paths.provisioned_r_home(probe)),
            "micromamba": str(paths.micromamba_exe(probe)),
            "package_cache": str(paths.pkgs_dir(probe)),
            "logs": str(paths.log_dir(probe)),
            "state_file": str(paths.state_file(probe)),
        },
        "exists": {
            "root": root.exists(),
            "env_prefix": env_prefix.exists(),
            "micromamba": paths.micromamba_exe(probe).is_file(),
        },
        "disk": {
            "used_bytes": _directory_size(root),
            "free_bytes": free,
        },
        "environment": {
            name: probe.environ.get(name)
            for name in paths.describe_env_vars()
        },
        "environment_help": paths.describe_env_vars(),
    }


def run(args) -> int:
    """Execute ``info``."""
    data = collect()

    if args.json:
        print(json.dumps(data, indent=2))
        return EXIT_OK

    out: list[str] = [f"robstattm-py {data['version']}", ""]
    out.append(f"platform: {data['platform_subdir']}")
    if data["platform_subdir"] == "unknown":
        out.append("  (R cannot be provisioned automatically here; install R yourself)")
    out.append("")

    out.append("Paths")
    for label, key in (
        ("root", "root"),
        ("R environment", "env_prefix"),
        ("R home", "provisioned_r_home"),
        ("micromamba", "micromamba"),
        ("package cache", "package_cache"),
        ("logs", "logs"),
        ("state file", "state_file"),
    ):
        out.append(f"  {label:<15} {data['paths'][key]}")
    out.append("")

    out.append("Disk")
    out.append(f"  used by us      {_human(data['disk']['used_bytes'])}")
    if data["disk"]["free_bytes"] is not None:
        out.append(f"  free            {_human(data['disk']['free_bytes'])}")
    out.append(f"  provisioned     {'yes' if data['exists']['env_prefix'] else 'no'}")
    out.append("")

    out.append("Environment variables")
    for name, description in data["environment_help"].items():
        value = data["environment"].get(name)
        shown = value if value else "(unset)"
        out.append(f"  {name}")
        out.append(f"      {description}")
        out.append(f"      current: {shown}")
    print("\n".join(out))
    return EXIT_OK


__all__ = ["add_parser", "collect", "run"]
