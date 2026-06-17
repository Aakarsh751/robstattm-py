"""Throwaway: extract every ```python block from the prose docs (not the
wrapper pages — validate_docs.py already covers those) and try to run each in
a fresh namespace. Reports which blocks fail so we can triage real bugs vs
intentional fragments."""
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

fails = 0
total = 0
for md in TARGETS:
    if not md.exists():
        continue
    text = md.read_text(encoding="utf-8")
    # One namespace per file: docs are read top-to-bottom, so a later block
    # may rely on imports/objects created by an earlier block in the same page.
    ns = {"__name__": "__doc_check__"}
    for i, m in enumerate(BLOCK.finditer(text), 1):
        code = textwrap.dedent(m.group(1))  # fences nested in lists carry indent
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

print(f"\n{total} executable blocks, {fails} failed")
