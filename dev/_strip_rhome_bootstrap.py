"""One-off: remove the hardcoded Windows ``R_HOME`` bootstrap from notebooks.

Every notebook used to open with::

    if sys.platform == 'win32' and 'R_HOME' not in os.environ:
        os.environ['R_HOME'] = r'C:\\Program Files\\R\\R-4.5.2'
        os.environ['PATH']   = r'C:\\Program Files\\R\\R-4.5.2\\bin\\x64;' + ...

which pinned a single R version on a single machine. ``robstattm_py`` now finds
R by itself (see ``robstattm_py/_renv/discovery.py``), so the block is both
unnecessary and actively wrong anywhere else.

Edits the raw JSON *text* line by line rather than round-tripping through
``json.load``/``json.dump``: these notebooks were written with differing indent
settings, and re-serialising them rewrites every line, burying the four-line
change in a thousand lines of reformatting.

Kept in ``dev/`` as a record of how the change was made; safe to re-run.
"""
from __future__ import annotations

import json
import pathlib
import sys

#: A raw JSON line is dropped when its decoded content matches any of these.
#: Plain substring tests — these strings appear nowhere else in the notebooks.
DROP_IF_ALL: tuple[tuple[str, ...], ...] = (
    ("if sys.platform", "R_HOME"),
    ("os.environ[", "R_HOME"),
    ("os.environ[", "PATH", "R-4.5.2"),
    ("point rpy2 at the R install",),
    ("Windows R_HOME setup",),
)


def should_drop(raw_line: str) -> bool:
    """True when this raw JSON line encodes a bootstrap source line."""
    stripped = raw_line.strip()
    if not stripped.startswith('"'):
        return False
    return any(all(token in stripped for token in group) for group in DROP_IF_ALL)


def strip_file(path: pathlib.Path) -> bool:
    """Rewrite ``path`` without the bootstrap. Returns True if it changed."""
    raw = path.read_text(encoding="utf-8")
    if "R_HOME" not in raw and "point rpy2" not in raw:
        return False

    kept = [line for line in raw.splitlines(keepends=True) if not should_drop(line)]
    new = "".join(kept)
    if new == raw:
        return False

    # Never write a notebook we have just broken: dropping the final element of
    # a source array would leave a trailing comma.
    try:
        json.loads(new)
    except json.JSONDecodeError as exc:
        print(f"  SKIP {path} (would break JSON: {exc})")
        return False

    path.write_text(new, encoding="utf-8", newline="")
    return True


def main(argv: list[str] | None = None) -> int:
    """Strip the bootstrap from every notebook under ``notebooks/``."""
    root = pathlib.Path(argv[0]) if argv else pathlib.Path("notebooks")
    changed = 0
    for path in sorted(root.rglob("*.ipynb")):
        if ".ipynb_checkpoints" in path.parts:
            continue
        if strip_file(path):
            changed += 1
            print(f"  cleaned {path}")
    print(f"{changed} notebook(s) cleaned")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
