# Documentation Standards

Production-grade. Every wrapper must comply before its quality gate (see `dev/design/quality_gates.md`) is met.

---

## 1. Docstring format

- **Format:** NumPy style (https://numpydoc.readthedocs.io/en/latest/format.html).
- **Renderer:** Sphinx `autodoc` + `numpydoc` + `sphinx-rtd-theme`.
- **All public functions, dataclasses, and classes** have a docstring. Private (`_underscore`) names may have a one-line summary.

### Required sections per public wrapper

```
Short one-line summary ending in a period.

Longer paragraph or two giving the statistical purpose and the relationship
to the R original. Reference the book section if applicable, e.g.
"Implements RobStatTM::lmrobdetMM (Maronna et al. 2019, §5.3)."

Parameters
----------
x : array_like, shape (n,) or (n, p)
    Description. Note expected dtype.
... (one entry per argument)

Returns
-------
LmrobdetMMResult
    Frozen dataclass; see Notes for field list.

Raises
------
TypeError
    When ...
ValueError
    When ...
RobStatTMRError
    When the underlying R call fails. The R traceback is attached as
    ``.r_traceback`` on the exception.
RobStatTMSetupError
    When R or RobStatTM is unavailable; call ``robstattm_py.check_setup()``
    for diagnostics.

Notes
-----
This is a thin rpy2 wrapper. The underlying R call is
``RobStatTM::lmrobdetMM(formula, data=data, control=control)``.
Outputs match the R return list field-by-field to machine precision
(see ``tests/regression/test_lmrobdet_mm.py``).

The R name `lmrobdet.control` is exposed in Python as
`lmrobdet_control` (R dot-to-Python underscore convention).

References
----------
.. [1] Maronna, R. A., Martin, R. D., Yohai, V. J., & Salibian-Barrera, M.
   (2019). *Robust Statistics: Theory and Methods (with R)* (2nd ed.).
   Wiley. Chapter 5.
.. [2] RobStatTM R man page: ``?lmrobdetMM``.

Examples
--------
>>> import robstattm_py as rpm
>>> from robstattm_py.datasets import mineral
>>> df = mineral()
>>> fit = rpm.lmrobdet_mm("zinc ~ copper", data=df)
>>> fit.coefficients
array([...])

See Also
--------
robstattm_py.regression.lmrobdet_dcml : DCML variant; higher efficiency.
robstattm_py.regression.step_lmrobdet : Robust stepwise model selection.
```

### Required sections per public dataclass

```
Short summary.

Longer description explaining the corresponding R return list and the
R-to-Python field renaming policy.

Attributes
----------
coefficients : np.ndarray, shape (p,)
    Estimated coefficient vector. Names available via ``coef_names``.
... one entry per field

Notes
-----
Frozen dataclass with __slots__. Field names are the snake_case of the
R names; see ``robstattm_py._converters._FIELD_MAP_R_TO_PY`` for the
mapping.
```

---

## 2. File-level docstring

Every Python module begins with a one-paragraph module docstring naming:
- the R function(s) it wraps,
- the book chapter,
- the dependency packages it needs (RobStatTM, plus any of pyinit/robustbase/rrcov).

Example:

```python
"""Robust MM-regression wrapper.

Wraps ``RobStatTM::lmrobdetMM`` (Maronna et al. 2019, §5.3, 5.9). Depends on
the R packages ``RobStatTM``, ``pyinit`` (default initialization), and
``robustbase`` (for τ-correction and robust leverage diagnostics).
"""
```

---

## 3. Type hints

- Mandatory on every public function signature.
- Use the aliases from `robstattm_py._typing` (`ArrayLike`, `FormulaLike`).
- Returns are precise dataclasses, not `dict` or `Any`.
- `py.typed` marker shipped in the wheel.

---

## 4. Examples in docstrings are executed

Every `Examples` block is executable. CI runs `pytest --doctest-modules` against `src/robstattm_py/`. Doctest examples may either:
- be marked `# doctest: +SKIP` if they require external resources, or
- use deterministic small inputs that match exactly.

Long examples belong in tutorial notebooks (`notebooks/tutorials/`), not in docstrings.

---

## 5. Sphinx configuration

- `conf.py` enables: `sphinx.ext.autodoc`, `sphinx.ext.napoleon` (or `numpydoc`), `sphinx.ext.intersphinx`, `sphinx.ext.viewcode`, `sphinx.ext.autosummary`, `sphinx_rtd_theme`.
- `intersphinx_mapping` points at NumPy, pandas, SciPy, scikit-learn.
- `nitpicky = True` and `-W` flag in CI, warnings fail the build.

API pages are generated via `sphinx-apidoc` + `autosummary`. The user does not hand-write per-function `.rst` files.

---

## 6. Examples gallery

`docs_sphinx/examples/` is built with the `sphinx-gallery` extension and pulls from `examples/` Python scripts. Each gallery example:
- reproduces one published figure or table from Maronna et al. (2019),
- has a header comment block linking back to the book section,
- runs end-to-end in CI.

---

## 7. README and CHANGELOG

- `README.md` at the repo root: installation, 30-second quickstart, link to RTD.
- `CHANGELOG.md` follows Keep-a-Changelog format. Every PR bumps the `[Unreleased]` section. PyPI releases get a dated header.

---

## 8. Notebook hygiene

- Strip outputs before committing (`nbstripout`).
- Tutorial notebooks live under `notebooks/tutorials/`; benchmark notebooks under `notebooks/benchmarks/`.
- Every notebook ends with a "Reproducibility" cell printing `robstattm_py.__version__`, R version, RobStatTM version, and the relevant CRAN packages' versions.

---

## 9. Templates

See `templates/`:
- `templates/wrapper.py.tmpl`, module + function skeleton.
- `templates/test_wrapper.py.tmpl`, pytest skeleton.
- `templates/docstring.md.tmpl`, a fill-in form for the docstring sections above.

Copy and edit; do not import.
