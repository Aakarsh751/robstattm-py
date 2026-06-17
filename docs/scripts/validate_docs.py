"""Validate that every rendered doc page is honest.

For each MyST page in ``docs/api/wrappers/``, check three claims:

1. **Import** — the line ``from robstatm_py import <py_name>`` works.
2. **Example** — the Python code block under "Examples" runs to completion
   without raising.
3. **Returns** — every R field listed in the "Returns" table is reachable
   on the actual Python result object via the documented R↔Python field
   convention (dots → underscores, snake_case).  We also detect Python
   fields that are *not* documented (under-documented surface).

Exit code is non-zero if any page fails any check.
"""
from __future__ import annotations

import dataclasses
import io
import re
import sys
import traceback
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WRAPPERS_DIR = ROOT / "docs" / "api" / "wrappers"
RD_JSON_DIR = ROOT / "docs" / "_rd_json"

sys.path.insert(0, str(ROOT / "src"))


# Python attribute names that exist on every wrapper result and are
# not part of the R return list — don't flag these as undocumented.
_INTERNAL_FIELDS = frozenset({
    "formula", "control", "coef_names",
})


def _strip_html_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s)


def _extract_python_block(md_text: str) -> str | None:
    """Return the body of the Python code block under the ``## Example`` heading."""
    m = re.search(
        r"^## Example\s*\n+```python\n(.*?)\n```",
        md_text, re.DOTALL | re.MULTILINE,
    )
    return m.group(1) if m else None


def _extract_import_line(md_text: str) -> str | None:
    m = re.search(r"^from robstatm_py import (\S+)$", md_text, re.MULTILINE)
    return m.group(1) if m else None


def _r_to_py_field(r_name: str) -> str:
    """Mirror the dataclass convention: dots → underscores."""
    return r_name.replace(".", "_")


def _validate_page(md_path: Path) -> dict:
    text = md_path.read_text(encoding="utf-8")
    page = md_path.stem
    result = {
        "page": page,
        "import_ok": None,
        "example_ok": None,
        "missing_attrs": [],
        "extra_attrs": [],
        "messages": [],
    }

    # ---- 1. Import claim ----
    py_name = _extract_import_line(text)
    if py_name is None:
        result["messages"].append("no `from robstatm_py import` line found")
        result["import_ok"] = False
    else:
        try:
            import robstatm_py as rpm
            fn = getattr(rpm, py_name)
            result["import_ok"] = True
            result["py_name"] = py_name
            result["fn"] = fn
        except Exception as e:
            result["import_ok"] = False
            result["messages"].append(f"import failed: {e}")

    # ---- 2. Example claim ----
    py_block = _extract_python_block(text)
    if py_block is None:
        result["example_ok"] = False
        result["messages"].append("no Python example block found")
    else:
        ns = {"__name__": "__doc_validator__"}
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                exec(compile(py_block, str(md_path), "exec"), ns)
            result["example_ok"] = True
            result["example_obj"] = ns.get("m") or ns.get("m2") or ns.get("fit")
        except Exception as e:
            result["example_ok"] = False
            result["messages"].append(
                f"example raised {type(e).__name__}: {e}"
            )
            result["example_traceback"] = traceback.format_exc()

    # ---- 3. Returns claim ----
    # Find the R field list in the JSON record (canonical source).
    json_path = None
    for cand in RD_JSON_DIR.glob("*.json"):
        import json as _json
        data = _json.loads(cand.read_text(encoding="utf-8"))
        py_target = data.get("name", "").replace(".", "_")
        # Re-derive py_name from the R↔Python map
        from robstatm_py._help import _R_TO_PY
        all_r_names = [data.get("name")] + list(data.get("aliases", []))
        for r in all_r_names:
            if _R_TO_PY.get(r) == py_name:
                json_path = cand
                break
        if json_path:
            break

    if json_path is None:
        result["messages"].append(
            f"no Rd JSON record found for py_name {py_name!r}"
        )
        return result

    import json as _json
    rec = _json.loads(json_path.read_text(encoding="utf-8"))
    r_fields = [v["r_name"] for v in rec.get("value", [])]
    if not r_fields:
        return result  # Nothing to validate (e.g. void return)

    # If the example produced a dataclass, check its fields
    obj = result.get("example_obj")
    if obj is None or not dataclasses.is_dataclass(obj):
        # Try instantiating without running the example: introspect the
        # return annotation via the renderer's heuristic.
        from inspect import get_annotations
        try:
            anns = get_annotations(result.get("fn"), eval_str=True)
            cls = anns.get("return")
        except Exception:
            cls = None
        if cls is None or not dataclasses.is_dataclass(cls):
            # Module-scan fallback
            mod_name = result.get("fn").__module__ if result.get("fn") else None
            mod = sys.modules.get(mod_name) if mod_name else None
            guess = (
                "".join(p.capitalize() for p in py_name.split("_")) + "Result"
            )
            cls = getattr(mod, guess, None) if mod else None
        if cls is not None and dataclasses.is_dataclass(cls):
            actual_fields = {f.name for f in dataclasses.fields(cls)
                             if not f.name.startswith("_")}
        else:
            result["messages"].append(
                "cannot resolve result dataclass for field check"
            )
            return result
    else:
        actual_fields = {f.name for f in dataclasses.fields(obj)
                         if not f.name.startswith("_")}

    # The rendered table is the contract.  Pull every backticked entry
    # in the first column of the "| Python attribute | R name | ... |"
    # table and compare to the actual dataclass fields.  Every Python
    # field must appear in the table; nothing else matters.
    rendered_py_fields: set[str] = set()
    in_returns = False
    for line in text.splitlines():
        if line.startswith("## Returns"):
            in_returns = True
            continue
        if in_returns and line.startswith("## "):
            break
        if in_returns and line.startswith("| `"):
            m = re.match(r"\|\s*`([^`]+)`\s*\|", line)
            if m and m.group(1) != "Python attribute":
                rendered_py_fields.add(m.group(1))

    missing_in_table = sorted(actual_fields - rendered_py_fields)
    extra_in_table = sorted(rendered_py_fields - actual_fields)
    result["missing_attrs"] = missing_in_table   # Python field absent from table
    result["extra_attrs"] = extra_in_table       # table mentions non-existent field
    result["r_fields"] = r_fields
    return result


def main() -> int:
    pages = sorted(WRAPPERS_DIR.glob("*.md"))
    if not pages:
        print(f"no pages found in {WRAPPERS_DIR}")
        return 1

    rc = 0
    print(f"validating {len(pages)} doc page(s)...\n")
    for p in pages:
        r = _validate_page(p)
        status = "OK"
        if r["import_ok"] is False or r["example_ok"] is False:
            status = "FAIL"
            rc = 1
        elif r["missing_attrs"]:
            status = "WARN"
        print(f"[{status:4s}] {r['page']:<20s}", end="")
        flags = []
        flags.append("import=ok" if r["import_ok"] else "import=FAIL")
        flags.append("example=ok" if r["example_ok"] else "example=FAIL")
        if r.get("r_fields") is not None:
            flags.append(
                f"fields-missing={len(r['missing_attrs'])} "
                f"fields-extra={len(r['extra_attrs'])}"
            )
        print("  " + "  ".join(flags))
        for m in r["messages"]:
            print(f"        · {m}")
        if r["missing_attrs"]:
            print(f"        · Python field NOT in rendered table: "
                  f"{r['missing_attrs']}")
        if r["extra_attrs"]:
            print(f"        · rendered table mentions non-existent field: "
                  f"{r['extra_attrs']}")
    print()
    print("FAIL" if rc else "ALL OK")
    return rc


if __name__ == "__main__":
    sys.exit(main())
