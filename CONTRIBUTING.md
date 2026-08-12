# Contributing

Thanks for looking. Bug reports are as welcome as code.

## Reporting a problem

Include the output of:

```bash
robstattm-py doctor --json
```

That single command captures your Python, rpy2, R, the full R-discovery trace
and every installed R package version — usually enough to diagnose the issue
without any back-and-forth.

Open issues at <https://github.com/Aakarsh751/robstattm-py/issues>.

## Getting set up

```bash
git clone https://github.com/Aakarsh751/robstattm-py
cd robstattm-py
python -m venv .venv && source .venv/bin/activate    # Windows: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev,plots,notebooks]"

robstattm-py doctor        # should say READY
```

If you have no R, `robstattm-py setup` will install one.

## Running the tests

```bash
# fast: skips notebook execution (~4 min)
RPM_SKIP_NOTEBOOKS=1 python -m pytest tests/ -q

# everything, including all 18 notebooks (~20 min)
python -m pytest tests/ -q

# R-free subset, seconds
python -m pytest tests/renv/ tests/plot/ -q
```

Everything must pass before a change lands.

## The one rule that matters

**Results must be bit-identical to R.** This package exists so that people can
use RobStatTM's estimators from Python and get the authors' numbers, not an
approximation. The suite compares field by field at `atol=0, rtol=0`.

Consequences:

- Never reimplement an estimator in Python. Call R.
- Never "fix up" a value R returned.
- A new wrapper needs a strict-tier test comparing it against a direct R call.

## Checking against R

When you need to know what R actually does — a default, an argument name, a
return field — read the R source, not our notes:

- Vendored source: `robstattm/RobStatTM-master/R/*.R`
- Installed package: `Rscript -e "print(formals(RobStatTM::lmrobdetMM))"`
- Man pages: `man/*.Rd`, extracted to `docs/_rd_json/`

`project_memory/robstattm-py-planning-docs/research/*.md` are working notes and have been wrong before.

## Releasing

Publishing to PyPI is documented step by step in
[`docs/RELEASING.md`](docs/RELEASING.md) — including creating the trusted
publisher, rehearsing on TestPyPI, and what cannot be undone afterwards.

## Documentation

Every code example must run:

```bash
python dev/_check_all_doc_code.py     # prose docs: README, getting-started, guides
python docs/scripts/validate_docs.py  # generated wrapper pages (needs R)
```

Pages must render correctly **both** as plain GitHub Markdown and under Sphinx,
so stick to standard Markdown — headings, tables, fenced code, `>` blockquotes.
No YAML frontmatter, no MyST-only directives in the body.

A block that genuinely cannot run (needs an optional R package, say) must say so
explicitly:

```markdown
<!-- doc-check: skip - needs the optional robcbi R package -->
```

Build the site with:

```bash
python -m sphinx -b html -W docs docs/_build/html
```

`-W` turns warnings into errors, which is how CI builds it.

## Tests for external R packages

Guard the R **package** *and* any R **dataset** it loads. These are different
things, and forgetting the second caused a month-long CI outage: the estimator
package was present on CI, the data package was not, and the test errored
instead of skipping.

`tests/conftest.py` has `_r_pkg_available` and `_r_dataset_available`. See
`tests/external/test_var_comprob.py` for the pattern.

Remember that a local machine with every optional package installed proves
nothing about CI.

## Style

- `python -m ruff check src/robstattm_py/ tests/` — new and changed code must
  be clean. There is pre-existing debt elsewhere; please do not mix a
  repo-wide reformat into a feature change.
- Type hints on public functions; numpydoc docstrings.
- Explain *why* in comments, not *what*. The non-obvious constraint, the reason
  for the ordering, the upstream bug being worked around — those are worth
  writing down. The code already says what it does.

## Pull requests

Keep the diff to one concern. Mechanical changes (renames, reformats) belong in
their own commit, separate from behaviour changes, so that review and `git
bisect` both stay useful.

Describe what you verified, and mention anything you could not check — an
untested platform is fine to say out loud.
