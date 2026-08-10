"""Run every ```python block in the prose docs and report which ones fail.

Complements ``docs/scripts/validate_docs.py``, which covers the generated
wrapper pages. This one covers the hand-written prose: getting-started, the
README, and every guide.

The rule the project holds itself to is that a documented example works. A block
that cannot run is either a bug in the docs or a fragment that should say so —
see ``SKIP_MARKER`` for the explicit opt-out, which exists so that
"needs an optional R package" is recorded in the page rather than showing up
here forever as an unexplained failure.

Exit status is non-zero when any block fails, so this is usable as a gate.
"""
from __future__ import annotations

import io
import re
import sys
import textwrap
import traceback
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DOCS = ROOT / "docs"
TARGETS = [
    DOCS / "getting-started.md",
    ROOT / "README.md",
    *sorted((DOCS / "guides").glob("*.md")),
]

# Tolerate fences indented inside list items (closing ``` may carry indent).
BLOCK = re.compile(r"```python\n(.*?)\n[ \t]*```", re.DOTALL)

# A bare signature display, e.g. "def pense(X, y, *, ...) -> PenseResult"
SIGNATURE = re.compile(r"^\s*def \w+\(.*\)\s*->\s*\w+\s*$", re.DOTALL)

#: Put this HTML comment immediately before a fence to exempt it, with a reason:
#:
#:     <!-- doc-check: skip - needs the optional robustvarComp R package -->
#:
#: Deliberately requires a reason and is visible in the source, so exemptions
#: stay honest and reviewable rather than accumulating silently.
SKIP_MARKER = re.compile(r"<!--\s*doc-check:\s*skip(?:\s*-\s*(?P<reason>[^>]*?))?\s*-->\s*$")


def _skip_reason(text: str, block_start: int) -> str | None:
    """Return the opt-out reason for the block starting at ``block_start``."""
    preceding = text[:block_start].rstrip()
    match = SKIP_MARKER.search(preceding)
    if not match:
        return None
    return (match.group("reason") or "no reason given").strip()


def main() -> int:
    """Execute every block and return an exit code."""
    fails = 0
    total = 0
    skipped = 0

    for md in TARGETS:
        if not md.exists():
            continue
        text = md.read_text(encoding="utf-8")
        # One namespace per file: docs are read top-to-bottom, so a later block
        # may rely on imports/objects created by an earlier block in the page.
        ns = {"__name__": "__doc_check__"}
        for i, m in enumerate(BLOCK.finditer(text), 1):
            code = textwrap.dedent(m.group(1))  # fences in lists carry indent

            reason = _skip_reason(text, m.start())
            if reason is not None:
                skipped += 1
                print(f"[skip] {md.name} block#{i}: {reason}")
                continue
            if ">>>" in code or "\n..." in code:
                print(f"[skip(repl)] {md.name} block#{i}")
                continue
            if SIGNATURE.match(code.strip()):
                print(f"[skip(sig)]  {md.name} block#{i}")
                continue

            total += 1
            try:
                with redirect_stdout(io.StringIO()):
                    exec(compile(code, f"{md.name}#block{i}", "exec"), ns)
                print(f"[ ok ] {md.name} block#{i}")
            except Exception as e:
                fails += 1
                print(f"[FAIL] {md.name} block#{i}: {type(e).__name__}: {e}")
                print("       " + "\n       ".join(
                    traceback.format_exc().splitlines()[-4:]))

    print(f"\n{total} executable blocks, {fails} failed, {skipped} explicitly skipped")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
