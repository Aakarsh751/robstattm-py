"""Render Rd JSON → MyST-Markdown wrapper pages.

Pilot implementation of M2 from ``project_memory/robstattm-py-planning-docs/documentation_plan.md``.

For each requested wrapper:
  1. Read ``docs/_rd_json/<RName>.json`` (produced by extract_rd.py).
  2. Look up the Python wrapper in ``robstattm_py._help._R_TO_PY``.
  3. Introspect the Python callable (signature + result dataclass fields).
  4. Build the R→Python argument map (with a small "Notes" column).
  5. Render through ``docs/templates/wrapper_page.md.jinja``.
  6. Write to ``docs/api/wrappers/<py_name>.md``.

The R→Python argument map is the **only** automated rename we do.  We
never search-replace R names inside free prose, because that produces
false positives (e.g. the prose talks about "the lmrob function from
robustbase", which is not a Python symbol we should rewrite).

Usage
-----
    python docs/scripts/render_rd.py --name lmrobdetMM
    python docs/scripts/render_rd.py --pilot     # 5 pilot wrappers
    python docs/scripts/render_rd.py --all
"""
from __future__ import annotations

import argparse
import dataclasses
import inspect
import json
import re
import sys
from pathlib import Path

import jinja2

ROOT = Path(__file__).resolve().parents[2]
RD_JSON = ROOT / "docs" / "_rd_json"
OUT_DIR = ROOT / "docs" / "api" / "wrappers"
TEMPLATE_DIR = ROOT / "docs" / "templates"
EXAMPLES_DIR = ROOT / "docs" / "examples"

sys.path.insert(0, str(ROOT / "src"))
from robstattm_py._help import _R_TO_PY  # noqa: E402

PILOT = ["lmrobdetMM", "covRobMM", "prcompRob", "BYlogreg", "locScaleM"]

# Pages whose Returns table is hand-authored (control objects: the table needs a
# per-field Default column the auto-generator can't produce, and the descriptions
# are curated against the R source). `--all` skips these so it never clobbers
# them; regenerate one explicitly with `--name <RName>` if you really mean to.
HAND_AUTHORED_PY = {"lmrobdet_control", "lmrobm_control"}


# ---------------------------------------------------------------- helpers

def _py_signature(fn) -> str:
    """One-line ``def f(...)`` reconstruction with sensible wrapping."""
    sig = inspect.signature(fn)
    name = fn.__name__
    params = [str(p) for p in sig.parameters.values()]
    one_line = f"def {name}({', '.join(params)}):"
    if len(one_line) <= 88:
        return one_line
    indent = " " * (len(f"def {name}(") )
    joined = (",\n" + indent).join(params)
    return f"def {name}(\n{indent}{joined},\n)"


def _result_dataclass(fn):
    """Best-effort: return the dataclass type that ``fn`` returns."""
    try:
        hints = inspect.get_annotations(fn, eval_str=True)
    except Exception:
        hints = {}
    ret = hints.get("return")
    if ret is not None and dataclasses.is_dataclass(ret):
        return ret
    # Fall back to scanning the function's module for a dataclass whose
    # name matches the wrapper's name + "Result".
    mod = sys.modules.get(fn.__module__)
    if mod is None:
        return None
    guess = "".join(p.capitalize() for p in fn.__name__.split("_")) + "Result"
    cls = getattr(mod, guess, None)
    if cls is not None and dataclasses.is_dataclass(cls):
        return cls
    return None


def _r_to_py_arg_map(r_args: list[dict], fn) -> list[dict]:
    """Pair R argument names with Python keyword names.

    The Python wrappers in this project keep R argument names with
    dots replaced by underscores (``na.action`` → ``na_action``).  We
    also annotate a "Notes" column for cases that diverge (e.g. when
    the Python wrapper adds an alternative input form like ``X, y``).
    """
    py_params = inspect.signature(fn).parameters
    rows: list[dict] = []
    for a in r_args:
        r = a["r_name"]
        py = r.replace(".", "_")
        note = ""
        if py not in py_params:
            note = "**not exposed** (handled internally)"
        rows.append({"r": r, "py": py, "note": note})
    # Detect Python-only parameters
    seen_py = {row["py"] for row in rows}
    for name, p in py_params.items():
        if name in seen_py or name in ("self",):
            continue
        rows.append({
            "r": "—",
            "py": name,
            "note": f"Python-only convenience (default `{p.default!r}`)"
                    if p.default is not p.empty else "Python-only",
        })
    return rows


def _format_annotation(ann) -> str:
    """Render a parameter/return annotation as a short, readable type string."""
    if ann is inspect.Parameter.empty or ann is None:
        return ""
    if isinstance(ann, str):
        s = ann
    else:
        s = getattr(ann, "__name__", None) or str(ann)
    # Strip module qualifiers and typing noise.
    s = s.replace("typing.", "")
    s = re.sub(r"\b[\w\.]+\.([A-Za-z_]\w*)", r"\1", s)  # foo.bar.Baz -> Baz
    s = s.replace("NoneType", "None")
    return s.strip()


def _format_default(p) -> str:
    """Render a parameter default for the docs table."""
    if p.default is inspect.Parameter.empty:
        return "*required*"
    d = p.default
    if isinstance(d, str):
        return f'`"{d}"`'
    return f"`{d!r}`"


# Descriptions for Python-only convenience parameters that the wrappers add on
# top of the R surface (the (X, y) array form and the regression shortcuts).
# Used only when the R man page has no matching argument.
_PY_PARAM_DESC: dict[str, str] = {
    "X": "Design matrix of predictors with shape `(n, p)` — the array-input "
         "alternative to the `formula` + `data` form.",
    "y": "Response vector of length `n` — used together with `X`.",
    "family": "Robust loss-function family shortcut (e.g. `\"mopt\"`, "
              "`\"bisquare\"`); sets the corresponding field on `control`.",
    "efficiency": "Target Gaussian efficiency shortcut (e.g. `0.95`); sets the "
                  "corresponding field on `control`.",
    "data": "A pandas `DataFrame` holding the variables referenced by `formula`.",
}


# Curated descriptions for result fields that are NOT in the R man page's
# \value{} block AND not described in the dataclass docstring's Attributes
# section.  These are mostly (a) input-echo / naming metadata the Python wrappers
# attach for downstream convenience, and (b) statistics that one wrapper's Rd
# documents but a sibling wrapper's sparser Rd omits (the meaning is identical).
# Wording matches the R man-page semantics where an equivalent field exists.
_WRAPPER_FIELD_DESC: dict[str, str] = {
    "formula": "The model formula used for the fit (echoes the input).",
    "control": "The control object used for the fit (echoes the input).",
    "coef_names": "Names of the estimated coefficients, aligned positionally "
                  "with `coefficients`.",
    "column_names": "Names of the input variables (columns of the input data), "
                    "aligned with the rows/columns of the estimates.",
    "component_names": "Names of the principal components (`PC1`, `PC2`, …).",
    "loss": "Value of the objective function at the final M-estimator.",
    "r_squared": "The robust multiple correlation coefficient (robust R²).",
    "degree_freedom": "The residual degrees of freedom.",
    "rweights_mm": "Robustness weights from the MM step (R `rweightsMM`), used "
                   "by the DCML estimator.",
    "t0": "The mixing proportion between the least-squares and robust regression "
          "estimators (DCML combines them as `t0·β_LS + (1−t0)·β_robust`).",
}


def _parameters(r_args: list[dict], fn) -> tuple[list[dict], list[dict]]:
    """Merge the Python signature with R argument descriptions.

    Returns ``(parameters, internal_args)`` where ``parameters`` is the
    ordered list of *exposed* Python parameters (each with type, default,
    and the description from the R man page when one matches), and
    ``internal_args`` are R arguments the wrapper handles internally
    (not exposed as Python parameters).

    Matching is case-SENSITIVE on the dot→underscore convention: Python `X`
    (a design matrix) must NOT be confused with R's `x` (a logical flag).
    """
    desc_by_py: dict[str, str] = {}
    for a in r_args:
        py_key = a["r_name"].replace(".", "_")
        desc_by_py[py_key] = a.get("description", "").replace("\n", " ").strip()

    sig = inspect.signature(fn)
    # In the regression wrappers that expose BOTH a formula/data form and an
    # (X, y) array form, R's own `x`/`y` are logical return-flags (kept as
    # internal args) — so Python `X`/`y` must use the array-input description,
    # not R's flag text. Detect that case by the presence of a `formula` param.
    dual_form = "formula" in sig.parameters
    params: list[dict] = []
    for name, p in sig.parameters.items():
        if name == "self" or p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        if dual_form and name in ("X", "y"):
            desc = _PY_PARAM_DESC[name]
        else:
            desc = desc_by_py.get(name) or _PY_PARAM_DESC.get(name, "")
        # Escape ``|`` so union types don't break the Markdown table columns.
        type_str = _format_annotation(p.annotation).replace("|", r"\|")
        params.append({
            "name": name,
            "type": type_str or "—",
            "default": _format_default(p),
            "description": desc.replace("|", r"\|"),
        })

    exposed = {p["name"] for p in params}
    internal = [
        {"r_name": a["r_name"],
         "description": a.get("description", "").replace("\n", " ").strip()}
        for a in r_args
        if a["r_name"].replace(".", "_") not in exposed
    ]
    return params, internal


def _attr_descriptions(cls) -> dict[str, str]:
    r"""Parse the numpydoc ``Attributes`` section of a result dataclass docstring.

    Returns ``{field_name: one_line_description}``.  This is the fallback
    source for result fields that the R man page's ``\value{}`` block does
    not document — RobStatTM's Rd files frequently list only a subset of the
    returned list, so without this the Returns table degrades to a generic
    placeholder.  The dataclass docstrings encode the real R-list semantics
    (e.g. which fields are ``None`` for which estimator), so they are the
    correct authority when the man page is silent.
    """
    if cls is None:
        return {}
    doc = inspect.getdoc(cls)
    if not doc:
        return {}
    lines = doc.splitlines()
    # Locate the numpydoc "Attributes" header (a line "Attributes" underlined
    # by dashes).  inspect.getdoc has already dedented, so it sits at column 0.
    start = None
    for i in range(len(lines) - 1):
        if lines[i].strip() == "Attributes" and set(lines[i + 1].strip()) == {"-"}:
            start = i + 2
            break
    if start is None:
        return {}

    out: dict[str, str] = {}
    cur: str | None = None
    buf: list[str] = []

    def _flush() -> None:
        if cur is not None:
            text = re.sub(r"\s+", " ", " ".join(buf)).strip()
            out[cur] = text.replace("``", "`")  # RST inline code -> Markdown

    n = len(lines)
    i = start
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if stripped and not line[0].isspace():
            # A following dashes line means a new numpydoc section begins.
            nxt = lines[i + 1].strip() if i + 1 < n else ""
            if nxt and set(nxt) == {"-"}:
                break
            # Otherwise this is a field entry: "name : type" or a bare "name".
            _flush()
            m = re.match(r"([A-Za-z_]\w*)", stripped)
            cur, buf = (m.group(1) if m else None), []
        elif stripped:
            buf.append(stripped)
        i += 1
    _flush()
    return out


def _method_summary(doc: str | None) -> str:
    """First sentence/line of a docstring, collapsed to one line."""
    if not doc:
        return ""
    text = inspect.cleandoc(doc).strip()
    # Take up to the first blank line (the summary paragraph), then 1st sentence.
    head = text.split("\n\n", 1)[0].replace("\n", " ").strip()
    m = re.match(r"(.+?\.)(\s|$)", head)
    return (m.group(1) if m else head).strip().replace("|", r"\|")


def _methods(result_cls) -> list[dict]:
    """Public, documented methods on a result dataclass (for the Methods table)."""
    if result_cls is None:
        return []
    out: list[dict] = []
    for name, member in inspect.getmembers(result_cls):
        if name.startswith("_"):
            continue
        if not callable(member):
            continue
        # Skip dataclass field descriptors and anything without a docstring.
        doc = inspect.getdoc(member)
        if not doc:
            continue
        try:
            sig = inspect.signature(member)
            params = [p for p in sig.parameters if p != "self"]
            sig_str = f"{name}({', '.join(params)})"
        except (TypeError, ValueError):
            sig_str = f"{name}(...)"
        out.append({"name": name, "signature": sig_str,
                    "summary": _method_summary(doc)})
    out.sort(key=lambda m: m["name"])
    return out


def _py_return_desc(fn, rec: dict) -> str:
    """Prose return description for wrappers that don't return a dataclass."""
    try:
        anns = inspect.get_annotations(fn, eval_str=True)
        ret = anns.get("return")
    except Exception:
        ret = None
    type_str = _format_annotation(ret) if ret is not None else ""
    rd_value = rec.get("value", [])
    if rd_value:
        bits = "; ".join(
            f"`{v['r_name']}` — {v['description'].replace(chr(10), ' ').strip()}"
            for v in rd_value
        )
        prefix = f"Returns `{type_str}`. " if type_str else "Returns: "
        return prefix + bits
    if type_str:
        return f"Returns `{type_str}`."
    return "See the description above for what this function returns."


def _r_example(rec: dict, py_name: str) -> str:
    """Return the 'Equivalent R code' block for ``py_name``.

    Preference order:
      1. ``docs/examples/<py_name>.R`` (hand-authored) — used verbatim. Provide
         this when the hand-authored Python example uses a different dataset or
         workflow than the R man page, so the two blocks are genuinely
         equivalent (same data, same calls).
      2. The R man page's ``\examples{}`` (Rd ``\%`` unescaped to ``%``).
    """
    override = EXAMPLES_DIR / f"{py_name}.R"
    if override.exists():
        return override.read_text(encoding="utf-8").replace("\\%", "%").strip()
    return (rec.get("examples_r", "") or "").replace("\\%", "%").strip()


def _python_example(rec: dict, py_name: str) -> str:
    """Return a working Python example for ``py_name``.

    Preference order:
      1. ``docs/examples/<py_name>.py`` (hand-authored, used verbatim)
      2. Auto-translation of the R example (best-effort regex rules)
      3. A bare "(no example)" placeholder

    Hand-authored examples are validated by
    ``docs/scripts/validate_docs.py`` — every page must execute.
    """
    override = EXAMPLES_DIR / f"{py_name}.py"
    if override.exists():
        return override.read_text(encoding="utf-8").rstrip()

    r_src = rec.get("examples_r") or ""
    if not r_src:
        return f"# (no R example available — see ``tests/`` for usage)"

    s = r_src
    s = re.sub(r"data\(([^,)]+),\s*package\s*=\s*['\"]([^'\"]+)['\"]\s*\)",
               r"\1 = rpm.datasets.load('\2', '\1')", s)
    s = re.sub(r"data\(([^)]+)\)",
               r"\1 = rpm.datasets.load('RobStatTM', '\1')", s)
    s = re.sub(r"\bsummary\(([^)]+)\)", r"\1.summary()", s)
    s = re.sub(r"\bprint\(([^)]+)\)", r"print(\1)", s)
    # m2 <- foo(...)  →  m2 = foo(...)
    s = re.sub(r"\s*<-\s*", " = ", s)
    # Rewrite the function call itself
    for rname, pname in _R_TO_PY.items():
        s = re.sub(rf"\b{re.escape(rname)}\(", f"rpm.{pname}(", s)
    # Quote bare R formulas:  foo(Y ~ ., data=...)  ->  foo("Y ~ .", data=...)
    s = re.sub(
        r"(\([^)]*?)\b([A-Za-z_][A-Za-z0-9_]*)\s*~\s*([^,\)]+?)(,|\))",
        lambda m: f'{m.group(1)}"{m.group(2)} ~ {m.group(3).strip()}"{m.group(4)}',
        s,
    )
    # Prepend an import; hand-authored overrides carry their own.
    return "import robstattm_py as rpm\n\n" + s.strip()


# ---------------------------------------------------------------- main

def render_one(r_name: str, env: jinja2.Environment) -> Path:
    py_name = _R_TO_PY.get(r_name)
    if py_name is None:
        raise KeyError(f"no Python mapping for R name {r_name!r}")

    import robstattm_py as rpm
    fn = getattr(rpm, py_name, None)
    if fn is None:
        raise AttributeError(f"robstattm_py has no attribute {py_name!r}")

    rd_path = RD_JSON / f"{r_name}.json"
    if not rd_path.exists():
        # Some Rd files have a \name{} that differs from their filename
        # (e.g. BYlogreg.Rd has \name{logregBY}).  Scan the directory.
        for cand in RD_JSON.glob("*.json"):
            data = json.loads(cand.read_text(encoding="utf-8"))
            if r_name in (
                data.get("name"), cand.stem, *data.get("aliases", [])
            ):
                rd_path = cand
                break
        else:
            raise FileNotFoundError(
                f"no JSON for R name {r_name!r} — run extract_rd.py first"
            )
    rec = json.loads(rd_path.read_text(encoding="utf-8"))

    result_cls = _result_dataclass(fn)
    py_module = (
        fn.__module__.replace("robstattm_py.", "").rsplit(".", 1)[0]
        if "." in fn.__module__.replace("robstattm_py.", "")
        else fn.__module__.replace("robstattm_py.", "")
    )

    # Build the Python-grounded Returns table.  The R man page lists the
    # full R return list; the Python wrapper exposes a curated subset.
    # The table shows the *Python* fields (because that's what the user
    # accesses) with their R origin name pulled from the Rd ``\value{}``.
    py_fields: list[dict] = []
    omitted: list[dict] = []
    if result_cls is not None:
        actual_fields = {
            f.name for f in dataclasses.fields(result_cls)
            if not f.name.startswith("_")
        }
        rd_value = rec.get("value", [])
        # Map dot→underscore plus case-insensitive (handles ``scale.S``).
        rd_by_pyname: dict[str, dict] = {}
        for v in rd_value:
            py_key = v["r_name"].replace(".", "_")
            rd_by_pyname.setdefault(py_key, v)
            rd_by_pyname.setdefault(py_key.lower(), v)
        # Fallback descriptions from the dataclass docstring for fields the
        # R man page's \value{} does not document (see _attr_descriptions).
        attr_desc = _attr_descriptions(result_cls)
        for f in dataclasses.fields(result_cls):
            if f.name.startswith("_"):
                continue
            rd = rd_by_pyname.get(f.name) or rd_by_pyname.get(f.name.lower())
            if rd:
                field_r_name = rd["r_name"]
                description = rd["description"].replace("\n", " ").replace("|", r"\|")
            else:
                field_r_name = "—"
                fallback = attr_desc.get(f.name) or _WRAPPER_FIELD_DESC.get(f.name, "")
                description = (
                    fallback.replace("|", r"\|") if fallback
                    else "Python wrapper field — see the result class docstring."
                )
            py_fields.append({
                "py_name": f.name,
                "r_name": field_r_name,
                "description": description,
            })
        # R fields in the Rd that don't appear on the Python dataclass.
        for v in rd_value:
            py_key = v["r_name"].replace(".", "_")
            if py_key in actual_fields or py_key.lower() in {
                a.lower() for a in actual_fields
            }:
                continue
            omitted.append({
                "r_name": v["r_name"],
                "description": v["description"].replace("\n", " "),
            })

    parameters, internal_args = _parameters(rec.get("arguments", []), fn)

    ctx = {
        "r_name": r_name,
        "py_name": py_name,
        "py_module": py_module,
        "title": (rec.get("title", "") or "").replace("\n", " ").strip(),
        "description": rec.get("description", "").strip(),
        "py_signature": _py_signature(fn),
        "parameters": parameters,
        "internal_args": internal_args,
        "py_result_class": result_cls.__name__ if result_cls else "result",
        "py_fields": py_fields,
        "omitted_r_fields": omitted,
        "py_return_desc": _py_return_desc(fn, rec) if not py_fields else "",
        "methods": _methods(result_cls),
        "details": rec.get("details", "").strip(),
        "sections": rec.get("sections", {}),
        # Equivalent R code: a hand-authored docs/examples/<py>.R override when
        # present (so it matches the Python example's data/workflow), else the
        # R man page's \examples{} with Rd ``\%`` unescaped to ``%``.
        "examples_r": _r_example(rec, py_name),
        "py_example": _python_example(rec, py_name),
        "seealso": rec.get("seealso", []),
        "references": rec.get("references", "").strip(),
        "author": rec.get("author", "").strip(),
        "r_to_py": _R_TO_PY,
    }

    template = env.get_template("wrapper_page.md.jinja")
    out = OUT_DIR / f"{py_name}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(template.render(**ctx), encoding="utf-8")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", help="single R-name to render")
    ap.add_argument("--pilot", action="store_true",
                    help="render the 5 pilot wrappers")
    ap.add_argument("--all", action="store_true",
                    help="render every R name in the map")
    args = ap.parse_args()

    if not (args.name or args.pilot or args.all):
        ap.error("pass --name <RName>, --pilot, or --all")

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR)),
        trim_blocks=False,
        lstrip_blocks=False,
        keep_trailing_newline=True,
    )

    if args.name:
        targets = [args.name]
    elif args.pilot:
        targets = PILOT
    else:
        # One page per unique Python wrapper. Keep the first R name that maps
        # to each py_name AND has an Rd JSON on disk (so we pick the canonical
        # documented alias, e.g. covRobMM over MMultiSHR).
        json_stems = {p.stem for p in RD_JSON.glob("*.json")}
        seen: set[str] = set()
        targets = []
        for r_name, py_name in _R_TO_PY.items():
            if py_name in seen:
                continue
            if r_name in json_stems:
                targets.append(r_name)
                seen.add(py_name)
        # Any py_name whose canonical alias lacked a JSON: fall back to first alias.
        for r_name, py_name in _R_TO_PY.items():
            if py_name not in seen:
                targets.append(r_name)
                seen.add(py_name)

    # `--all` must not overwrite hand-authored control pages; `--name` may.
    if args.all:
        targets = [r for r in targets if _R_TO_PY.get(r) not in HAND_AUTHORED_PY]

    for r_name in targets:
        try:
            out = render_one(r_name, env)
            print(f"[OK]   {r_name:<20s} -> {out.relative_to(ROOT)}")
        except Exception as e:
            print(f"[FAIL] {r_name:<20s} {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
