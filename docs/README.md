# RobStatTM-Py documentation

This folder holds the documentation site and the pipeline that generates the
per-function API pages.

## Reading the docs

- **Start at [`index.md`](index.md)** — the landing page.
- **[`getting-started.md`](getting-started.md)** — install, verify, first fit.
- **[`api/index.md`](api/index.md)** — every wrapped function, grouped by topic.
  Individual pages live in [`api/wrappers/`](api/wrappers/).
- **[`guides/`](guides/)** — datasets, ψ-loss families, utilities, result methods.

Every page is plain GitHub-Flavored Markdown, so it renders correctly here on
GitHub **and** builds into a Sphinx site (see below).

## Building the Sphinx site

```bash
cd robstattm-py
pip install -e ".[docs]"
python -m sphinx -b html docs docs/_build/html
# open docs/_build/html/index.html
```

The build does **not** import `robstattm_py`, so it works without R installed —
the API pages are pre-generated Markdown.

## How the API pages are generated

The `api/wrappers/*.md` pages are produced from the R man pages by a small,
three-step pipeline in [`scripts/`](scripts/):

1. **`extract_rd.py`** — parses RobStatTM's `man/*.Rd` files into JSON
   (`_rd_json/*.json`). Point it at the upstream sources with the
   `ROBSTATTM_MAN_DIR` env var if they are not at the repo root.
   ```bash
   python docs/scripts/extract_rd.py --all
   ```
2. **`render_rd.py`** — renders each JSON record through
   [`templates/wrapper_page.md.jinja`](templates/wrapper_page.md.jinja),
   merging in the live Python signature, return-field table, and result-object
   methods. Hand-authored examples in [`examples/`](examples/) are used verbatim.
   ```bash
   python docs/scripts/render_rd.py --all
   ```
3. **`validate_docs.py`** — executes every page's Python example against R and
   checks that each documented return field is reachable. Run it (with R
   configured) before committing doc changes.
   ```bash
   python docs/scripts/validate_docs.py
   ```

To add or improve an example, edit `examples/<py_name>.py` and re-run steps 2–3.

## Implementation / design docs

The Markdown files at the top level of this folder (`architecture.md`,
`coverage_matrix.md`, `validation_strategy.md`, `user_interface.md`, …) and
`research/` are internal design notes, not part of the published site (they are
excluded in `conf.py`).
