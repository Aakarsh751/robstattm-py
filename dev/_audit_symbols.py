"""Find symbols defined in src/ that nothing outside their own file references.

Deliberately crude and deliberately noisy: it reports *candidates*, and every
one still has to be read in context before it is touched. A name that only ever
appears at its own definition is a strong signal; a name with two hits is not.

Counts textual occurrences rather than resolving imports, because the package is
reachable four different ways (source, tests, docs code blocks, notebooks) and a
real audit has to see all four. Textual matching over-counts common words, which
is the safe direction to err in.

Usage:  python dev/_audit_symbols.py
"""
from __future__ import annotations

import ast
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "robstattm_py"

# Every place a src symbol could legitimately be used from.
SEARCH_DIRS = ["src", "tests", "exploration", "dev", "docs", "notebooks", "examples"]
SKIP_PARTS = {"_build", "__pycache__", ".ruff_cache", ".pytest_cache", "dist", "_rd_json"}


def iter_files() -> list[Path]:
    out: list[Path] = []
    for d in SEARCH_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            if set(p.parts) & SKIP_PARTS:
                continue
            if p.suffix in {".py", ".md", ".ipynb", ".rst", ".yml", ".yaml", ".toml", ".cfg"}:
                out.append(p)
    for extra in ("README.md", "CHANGELOG.md", "CONTRIBUTING.md", "pyproject.toml"):
        p = ROOT / extra
        if p.exists():
            out.append(p)
    return out


def defined_symbols() -> dict[str, list[tuple[str, int]]]:
    """symbol -> [(relative path, lineno)] for every top-level def/class in src/."""
    defs: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for p in sorted(SRC.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        rel = p.relative_to(ROOT).as_posix()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defs[node.name].append((rel, node.lineno))
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id.isupper():
                        defs[t.id].append((rel, node.lineno))
    return defs


def main() -> int:
    defs = defined_symbols()
    texts = {p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8", errors="replace")
             for p in iter_files()}

    report: list[dict] = []
    for name, sites in sorted(defs.items()):
        if len(name) <= 2:
            continue  # too short to match meaningfully
        pat = re.compile(rf"\b{re.escape(name)}\b")
        own_files = {f for f, _ in sites}
        hits_by_file = {}
        for rel, text in texts.items():
            n = len(pat.findall(text))
            if n:
                hits_by_file[rel] = n
        external = {f: n for f, n in hits_by_file.items() if f not in own_files}
        internal = sum(n for f, n in hits_by_file.items() if f in own_files)
        report.append({
            "name": name,
            "defined_at": sites,
            "internal_hits": internal,
            "external_files": external,
        })

    dead = [r for r in report if not r["external_files"] and r["internal_hits"] <= 1]
    local_only = [r for r in report
                  if not r["external_files"] and 1 < r["internal_hits"] <= 2]

    print(f"src symbols scanned: {len(report)}")
    print(f"\n=== NEVER REFERENCED ANYWHERE (definition is the only hit): {len(dead)} ===")
    for r in dead:
        print(f"  {r['name']:<40} {r['defined_at'][0][0]}:{r['defined_at'][0][1]}")
    print(f"\n=== ONE OTHER MENTION, SAME FILE ONLY: {len(local_only)} ===")
    for r in local_only:
        print(f"  {r['name']:<40} {r['defined_at'][0][0]}:{r['defined_at'][0][1]}")

    (ROOT / "dev" / "_audit_symbols.json").write_text(
        json.dumps(report, indent=1), encoding="utf-8"
    )
    print("\nFull map written to dev/_audit_symbols.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
