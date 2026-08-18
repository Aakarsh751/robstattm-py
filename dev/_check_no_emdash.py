"""House-style guard: no em dashes (U+2014) anywhere in the source tree.

The project's written style replaces the em dash with ordinary punctuation
(a comma, colon, parentheses, or a spaced hyphen, whichever the sentence
wants). This script both *enforces* that and *applies* the common fix.

Usage
-----
    python dev/_check_no_emdash.py                # scan the repo, exit 1 if any
    python dev/_check_no_emdash.py PATH [PATH...] # scan only these paths
    python dev/_check_no_emdash.py --fix PATH...  # rewrite the safe cases

``--fix`` rewrites the two unambiguous cases: a ``space em-dash space`` aside
becomes a comma, and in a heading or a list item the term/definition dash
becomes a spaced hyphen (which reads better there than a comma). Anything else
(a bare em dash, a table-cell placeholder) is left in place and reported, so
the author can pick the right punctuation by hand rather than have the tool
guess.

CI runs the check form (no ``--fix``); a non-zero exit fails the build.

The em-dash character is spelled ``chr(0x2014)`` throughout so that running
``--fix`` over this file never rewrites the tool's own patterns.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

EM = chr(0x2014)

# Only text formats. Binary assets (png, rda, ...) are skipped entirely.
TEXT_SUFFIXES = {
    ".py", ".md", ".rst", ".txt", ".ipynb", ".jinja", ".toml", ".cfg",
    ".yml", ".yaml", ".R", ".r", ".in",
}
SKIP_DIRS = {
    ".git", "__pycache__", "_build", "_rd_json", "node_modules", ".ruff_cache",
    ".pytest_cache", ".venv", "dist", "build", "_figures", "figures",
}
# Generated Rd JSON mirrors upstream R text verbatim; never rewrite it.
SKIP_DIR_PATHS = {"docs/_rd_json"}

# em-dash hugging a line break (a wrapped aside) -> comma
_EOL = re.compile(r" ?" + EM + r"(\s*\r?\n)")
# space em-dash space (the dominant inline "aside") -> comma
_ASIDE = re.compile(r" ?" + EM + r" ")
# a heading, or a list item ("- ", "* ", "1. "): its first dash usually
# separates a term from its definition, where a spaced hyphen reads best.
_TERM_LINE = re.compile(r"^\s*(#|[-*+] |\d+\. )")


def _iter_files(paths: list[Path]):
    for p in paths:
        if p.is_file():
            yield p
            continue
        for child in p.rglob("*"):
            if child.is_dir():
                continue
            rel = child.as_posix()
            if any(part in SKIP_DIRS for part in child.parts):
                continue
            if any(s in rel for s in SKIP_DIR_PATHS):
                continue
            if child.suffix in TEXT_SUFFIXES:
                yield child


def _fix_text(text: str) -> str:
    text = _EOL.sub(r",\1", text)
    out_lines = []
    for line in text.split("\n"):
        if EM not in line:
            out_lines.append(line)
            continue
        if _TERM_LINE.match(line):
            # First term/definition dash -> spaced hyphen; any further asides
            # on the same line -> comma.
            head, sep, rest = line.partition(f" {EM} ")
            if sep:
                line = head + " - " + _ASIDE.sub(", ", rest)
            else:
                line = _ASIDE.sub(", ", line)
        else:
            line = _ASIDE.sub(", ", line)
        out_lines.append(line)
    return "\n".join(out_lines)


def main(argv: list[str]) -> int:
    fix = "--fix" in argv
    args = [a for a in argv if a != "--fix"]
    roots = [Path(a) for a in args] or [Path(".")]

    residual: list[tuple[str, int, str]] = []
    fixed_files = 0
    for f in _iter_files(roots):
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if EM not in text:
            continue
        if fix:
            new = _fix_text(text)
            if new != text:
                f.write_text(new, encoding="utf-8")
                fixed_files += 1
            text = new
            if EM not in text:
                continue
        for i, line in enumerate(text.splitlines(), 1):
            if EM in line:
                residual.append((f.as_posix(), i, line.strip()))

    if fix:
        print(f"Rewrote {fixed_files} file(s).")
    if residual:
        print(f"\n{len(residual)} em dash(es) need a hand-picked replacement:")
        for path, ln, line in residual:
            print(f"  {path}:{ln}: {line[:110]}")
        return 1
    print("OK: no em dashes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
