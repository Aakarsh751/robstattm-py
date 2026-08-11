"""Report any string literal in the package that a cp1252 console cannot print.

Windows' default console encoding is cp1252 when stdout is a pipe. Printing a
character outside it raises UnicodeEncodeError — not a garbled character, an
exception — so a user-facing message containing one is a crash waiting for the
first Windows user who redirects output.

Only *runtime output* matters: docstrings and comments are never encoded to the
console. This walks the AST and checks string constants that are not docstrings.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def docstring_nodes(tree: ast.AST) -> set[int]:
    """ids() of the Constant nodes that serve as docstrings."""
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if isinstance(body[0].value.value, str):
                    out.add(id(body[0].value))
    return out


def main() -> int:
    problems = []
    for target in ("src", "examples"):
        for path in sorted((ROOT / target).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            skip = docstring_nodes(tree)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                    continue
                if id(node) in skip:
                    continue
                bad = sorted({c for c in node.value if not _cp1252_ok(c)})
                if bad:
                    problems.append(
                        (path.relative_to(ROOT).as_posix(), node.lineno, bad,
                         node.value.strip()[:70])
                    )

    if not problems:
        print("No non-cp1252 characters in runtime strings.")
        return 0
    print(f"{len(problems)} runtime string(s) a cp1252 console cannot encode:\n")
    for rel, lineno, bad, preview in problems:
        # Escape before printing: this script must not fall over the thing it
        # is reporting.
        chars = ", ".join(f"U+{ord(c):04X}" for c in bad)
        safe = preview.encode("ascii", "backslashreplace").decode("ascii")
        print(f"  {rel}:{lineno}  [{chars}]\n      {safe}")
    return 1


def _cp1252_ok(char: str) -> bool:
    try:
        char.encode("cp1252")
    except UnicodeEncodeError:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
