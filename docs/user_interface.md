# User Interface Design

**Goal:** a Python user who knows zero R can use every RobStatTM function as naturally as they use scikit-learn or statsmodels. A Python user who is transcribing R code from the textbook can do it line-by-line, by name lookup, in under 10 seconds per function.

This document is the **ergonomics specification** that complements `docs/architecture.md` (the engineering structure). Where architecture says "frozen dataclass," this says "and the user types this to get it."

---

## 1. The 60-second user story

```python
# 1. Install
$ pip install robstatm-py
$ python -c "import robstatm_py; robstatm_py.check_setup()"
# ✓ R 4.5.1   ✓ RobStatTM 1.0.12   ✓ pyinit 1.1.1   ✓ robustbase 0.99-4   ✓ rrcov 1.7-6

# 2. Use
>>> import robstatm_py as rpm
>>> data = rpm.datasets.mineral()           # pandas DataFrame, columns match R
>>> fit  = rpm.lmrobdet_mm("zinc ~ copper", data=data)
>>> fit                                      # __repr__: short summary
<LmrobdetMMResult: zinc ~ copper, scale=2.31, R²=0.86, converged in 7 iter>
>>> print(fit.summary())                     # long summary, mirrors R summary()
... call: lmrobdetMM(formula = zinc ~ copper, data = mineral)
... coefficients:        Estimate   Std.Err   t-value   Pr(>|t|)
... (Intercept)            -3.12      1.45     -2.15      0.038
... copper                  0.34      0.04      8.45      0.000
... robust R²: 0.861   robust scale: 2.31   converged: True (7 iter)

# 3. Plot
>>> fig = rpm.plot.residuals(fit)            # matplotlib Axes
>>> fig = rpm.plot.residuals(fit, backend="r")  # PNG from R's plot.lmrobdetMM

# 4. Tests / diagnostics
>>> rpm.rob_linear_test(fit, drop=["copper"])
>>> rpm.step_lmrobdet(fit, direction="both")
>>> fit.drop1()                               # single-term-deletion RFPE table
>>> fit.hatvalues()
```

If any line in the story above is **not** obvious to a working Python data scientist, the design has failed.

---

## 2. Top-level API surface

### 2.1 Flat re-exports — the user's default import

```python
import robstatm_py as rpm
# everything below is available as rpm.<name>:

rpm.loc_scale_m       rpm.m_scale
rpm.lmrobdet_mm       rpm.lmrobdet_dcml      rpm.lmrob_m
rpm.lmrobdet_control  rpm.lmrobm_control
rpm.step_lmrobdet     rpm.rob_linear_test    rpm.pyinit
rpm.cov_rob           rpm.cov_rob_mm         rpm.cov_rob_rocke
rpm.cov_classic       rpm.kurt_sd_new        rpm.fastmve
rpm.pca_rob_s         rpm.prcomp_rob
rpm.by_logreg         rpm.wby_logreg         rpm.wml_logreg
rpm.dcml              rpm.cov_dcml           rpm.mmpy            rpm.smpy
rpm.invtr2            rpm.lmrobdet_mm_rfpe   rpm.refine_sm
rpm.set_seed          rpm.check_setup        rpm.__version__

# submodules for namespaced access:
rpm.datasets          # 20 dataset loaders
rpm.psi               # bisquare, huber, mopt, opt, rho, rhoprime, rhoprime2
rpm.plot              # residuals(), distance_distance(), scree(), qq()
rpm.benchmarks        # only loaded when needed; keeps top-level light
```

**Rationale:** scikit-learn / statsmodels users expect a flat API. R users transcribing code recognize the names with snake_case translation.

### 2.2 Submodule access — for users who prefer grouping

```python
from robstatm_py.regression import lmrobdet_mm, step_lmrobdet
from robstatm_py.covariance import cov_rob_mm, cov_rob_rocke
from robstatm_py.pca import pca_rob_s
```

Both forms work; both are documented; tutorial notebooks pick whichever is clearer in context.

### 2.3 R-name aliases — optional, opt-in

A Python user transcribing the textbook may want to keep the R name verbatim. We provide aliases gated behind a single import:

```python
from robstatm_py.compat_r import *
# Now: lmrobdetMM, lmrobdet.control (via a Python-legal alias),
# scaleM, locScaleM, MLocDis, covRobMM, MMultiSHR, ...

fit = lmrobdetMM("zinc ~ copper", data=data)   # works, identical to lmrobdet_mm
```

R dotted names that are not Python-legal get **two** aliases:
- `lmrobdet_control` (canonical)
- `lmrobdetcontrol` (no separator, last-resort)

But not `lmrobdet.control` — that would require `getattr`. The R-to-Python name map (§5 below) is the single source of truth.

---

## 3. Formula handling

R users write `y ~ x1 + x2 * x3`. Python users have three sensible options; we accept all three:

```python
# 1. R formula string (what most R-transcribers will paste)
fit = rpm.lmrobdet_mm("zinc ~ copper + zinc:lead", data=df)

# 2. Patsy-style string (works because R syntax is a subset for these cases)
fit = rpm.lmrobdet_mm("zinc ~ copper + zinc:lead", data=df)
# ↑ same; we use rpy2's ro.Formula() to pass the string straight through

# 3. Explicit X, y arrays (for users who don't want a formula at all)
fit = rpm.lmrobdet_mm(X=df[["copper", "lead"]], y=df["zinc"])
```

**Implementation:**
- If `formula` is a string → wrap as `ro.Formula(formula)`, pass to R; R handles parsing.
- If `X, y` provided → construct `y ~ .` formula internally; pass `data = pd.concat([y, X], axis=1)` to R.
- **Never** ourselves parse the formula in Python (patsy syntax diverges from R in subtle ways like `*` interaction operator behavior with categoricals).

This is documented in every wrapper's `Notes` section.

---

## 4. Dataset loaders

```python
>>> df = rpm.datasets.mineral()
>>> df.head()
   copper  zinc  lead
0    18.0  140.0   ...
...
>>> rpm.datasets.mineral.__doc__
'Mineral content of pine needles. n=53, p=3. Used in Maronna et al. (2019) §5.x to demonstrate the effect of high-leverage outliers on classical OLS vs. lmrobdetMM. Original source: ...'

>>> rpm.datasets.list()
['alcohol', 'algae', 'biochem', 'breslow_dat', 'bus', 'flour', 'glass',
 'hearing', 'image', 'leuk_dat', 'mineral', 'neuralgia', 'oats', 'resex',
 'shock', 'skin', 'stackloss', 'vehicle', 'waste', 'wine']
```

Each loader returns a **pandas DataFrame** with R column names preserved (dotted R names → underscored). The docstring is **lifted verbatim** from the corresponding `.Rd` man page (parsed once at build time, stored as a Python string).

Implementation: `robstatm_py.datasets.mineral()` calls `R('data(mineral, package="RobStatTM"); mineral')` and converts. Cached after first call.

---

## 5. The R → Python name table (canonical)

A single dictionary in `robstatm_py._namemap` and a **rendered HTML page in the docs** so users can search.

| R name | Python name | Module | Notes |
|--------|-------------|--------|-------|
| `locScaleM` | `loc_scale_m` | `univariate` | alias `MLocDis` → `mlocdis` |
| `MLocDis` | `loc_scale_m` | `univariate` | (same function) |
| `scaleM` | `m_scale` | `univariate` | alias `mscale` also accepted |
| `mscale` | `m_scale` | `univariate` | (same) |
| `lmrobM` | `lmrob_m` | `regression` | |
| `lmrobM.control` | `lmrobm_control` | `regression` | |
| `lmrobdetMM` | `lmrobdet_mm` | `regression` | |
| `lmrobdet.control` | `lmrobdet_control` | `regression` | |
| `lmrobdetDCML` | `lmrobdet_dcml` | `regression` | |
| `step.lmrobdetMM` | `step_lmrobdet` | `regression` | (R name also accepted as `step.lmrobdetMM` is not Python-legal) |
| `rob.linear.test` | `rob_linear_test` | `regression` | alias `lsRobTestMM` → `ls_rob_test_mm`, `lmrobdetLinTest` → `lmrobdet_lin_test` |
| `lsRobTestMM` | `rob_linear_test` | `regression` | (same) |
| `lmrobdetLinTest` | `rob_linear_test` | `regression` | (same) |
| `pyinit` | `pyinit` | `regression` | name unchanged |
| `DCML` | `dcml` | `regression` | low-level |
| `cov.dcml` | `cov_dcml` | `regression` | |
| `MMPY` | `mmpy` | `regression` | |
| `SMPY` | `smpy` | `regression` | |
| `INVTR2` | `invtr2` | `regression` | robust R² |
| `lmrobdetMM.RFPE` | `lmrobdet_mm_rfpe` | `regression` | |
| `refine.sm` | `refine_sm` | `regression` | |
| `covRob` | `cov_rob` | `covariance` | generic dispatcher |
| `covRobMM` | `cov_rob_mm` | `covariance` | alias `MMultiSHR` → `mmulti_shr` |
| `MMultiSHR` | `cov_rob_mm` | `covariance` | (same) |
| `covRobRocke` | `cov_rob_rocke` | `covariance` | alias `RockeMulti` → `rocke_multi` |
| `RockeMulti` | `cov_rob_rocke` | `covariance` | (same) |
| `Multirobu` | `multirobu` | `covariance` | top-level dispatcher |
| `covClassic` | `cov_classic` | `covariance` | classical companion |
| `KurtSDNew` | `kurt_sd_new` | `covariance` | alias `initPP` → `init_pp` |
| `initPP` | `kurt_sd_new` | `covariance` | (same) |
| `fastmve` | `fastmve` | `covariance` | |
| `pcaRobS` | `pca_rob_s` | `pca` | alias `SMPCA` → `smpca` |
| `SMPCA` | `pca_rob_s` | `pca` | (same) |
| `prcompRob` | `prcomp_rob` | `pca` | |
| `BYlogreg` | `by_logreg` | `glm` | alias `logregBY` → `logreg_by` |
| `logregBY` | `by_logreg` | `glm` | (same) |
| `WBYlogreg` | `wby_logreg` | `glm` | alias `logregWBY` → `logreg_wby` |
| `WMLlogreg` | `wml_logreg` | `glm` | alias `logregWML` → `logreg_wml` |
| `bisquare`, `huber`, `mopt`, `moptv0`, `opt`, `optv0` | `psi.bisquare`, etc. | `psi` | |
| `rho`, `rhoprime`, `rhoprime2` | `psi.rho`, `psi.rhoprime`, `psi.rhoprime2` | `psi` | |
| `print.lmrobdetMM` | `__repr__` on result | n/a | S3 → dataclass method |
| `summary.lmrobdetMM` | `.summary()` method | n/a | |
| `drop1.lmrobdetMM` | `fit.drop1(scope=...)` method, or `rpm.drop1_lmrobdet(fit, scope=...)` | `regression` | Single-term-deletion RFPE table; implemented 2026-06-14 |
| `hatvalues.lmrob` | `.hatvalues()` method | n/a | works on all `lmrob_m` / `lmrobdet_mm` / `lmrobdet_dcml` results |

This table is **the single source of truth** for naming. Rendered as `docs_sphinx/r_to_python_name_map.html` and shipped on RTD.

---

## 6. Result-object ergonomics

A user must be able to do all of:

```python
fit = rpm.lmrobdet_mm("y ~ x1 + x2", data=df)

# 1. R-style field access (works because dataclass + reasonable field names)
coef = fit.coefficients

# 2. Dict-style access (some users prefer)
fit_dict = fit.to_dict()
coef = fit_dict["coefficients"]

# 3. Pandas integration
fit.coef_df()                 # pd.Series with names from R
fit.summary().to_pandas()     # pd.DataFrame of the summary table

# 4. Easy plotting
ax = fit.plot_residuals()     # matplotlib Axes; shortcut for rpm.plot.residuals(fit)
ax = fit.plot_qq()
ax = fit.plot_diagnostics()   # 2x2 grid like R's plot(lm)

# 5. Predict on new data
y_hat = fit.predict(X_new)
y_hat = fit.predict(new_df)   # accepts the same column names

# 6. Pickle / save
import pickle; pickle.dump(fit, open("fit.pkl", "wb"))

# 7. Round-trip back to R if the user needs to keep working in R
ro_fit = fit.to_r()           # returns the rpy2 RObject for downstream R analysis
```

Every result dataclass implements:
- `__repr__` (short summary, S3 print-equivalent)
- `summary()` (returns a `SummaryTable` with `__repr__` and `to_pandas()`)
- `to_dict()`, `to_r()`
- `.predict(...)` where applicable (regression, GLM)
- `.plot_<diagnostic>()` shortcuts that delegate to `rpm.plot`

These are **enforced by quality gate** — every wrapper PR ships with the appropriate methods or the gate fails.

---

## 7. Error messages

Two principles:

1. **Errors must tell the user what to do.** "RobStatTM not installed" is bad; "RobStatTM not installed. Run `install.packages('RobStatTM')` in R, or `robstatm_py.check_setup()` for details" is good.
2. **R tracebacks are surfaced, not hidden.** When R raises, the Python exception carries the R traceback as `.r_traceback` so the user can debug the R call.

```python
>>> rpm.lmrobdet_mm("zinc ~ copper", data=df_with_nan)
Traceback (most recent call last):
  ...
robstatm_py.RobStatTMRError: lmrobdetMM failed: missing values not allowed with na.action='fail'.

R traceback (from .r_traceback):
  Error in na.fail.default(...) : missing values in object
  ...

Hint: pass `na_action="omit"` to drop rows with NA, or pre-clean your data.
```

The "Hint:" line is a curated extension: the wrapper's argument-validation layer maps common R error keywords to actionable Python hints.

**R warnings are surfaced too, not just errors.** R defers warnings by default,
so a long fit used to end with nothing but rpy2's opaque
`There were 50 or more warnings` console line — the individual messages were
unrecoverable. Every R call now runs under a capture that forces immediate
emission and re-raises each message through Python's `warnings` machinery as a
`RobStatTMWarning`:

```python
>>> import warnings
>>> from robstatm_py import RobStatTMWarning, last_r_warnings
>>> with warnings.catch_warnings(record=True) as caught:
...     warnings.simplefilter("always")
...     fit = rpm.lmrob_m("y ~ x", data=hard_df, max_it=2)
>>> [str(w.message) for w in caught if issubclass(w.category, RobStatTMWarning)]
['M-step did NOT converge. Returning unconverged lM-estimate']

>>> last_r_warnings()          # messages from the most recent R call
['M-step did NOT converge. Returning unconverged lM-estimate']
```

Because this sits at the rpy2 console-callback layer it covers both the fit
call and the result methods (`.summary()`, `.predict()`, `.drop1()`, which refit
on the R side). Suppress them like any Python warning
(`warnings.simplefilter("ignore", RobStatTMWarning)`), or capture a block
explicitly with the `capture_r_warnings()` context manager.

---

## 8. `check_setup()` UX

```python
>>> rpm.check_setup()
RobStatTM-Py setup check
========================
Python:                3.11.6
robstatm_py:           0.1.0
rpy2:                  3.6.7                ✓
R:                     4.5.1 (2025-05-15)   ✓  R_HOME=/usr/local/Cellar/r/4.5.1
RobStatTM:             1.0.12               ✓
pyinit:                1.1.1                ✓
robustbase:            0.99-4               ✓
rrcov:                 1.7-6                ✓
pense:                 (not installed)      ⚠  stretch wrappers unavailable
GSE:                   (not installed)      ⚠  stretch wrappers unavailable

To install missing stretch packages, run in R:
  install.packages(c("pense", "GSE"))

Result: READY for core wrappers.  STRETCH WRAPPERS UNAVAILABLE.
```

Exits with `True` (READY) if all core packages present, `False` otherwise; prints an actionable report either way. Documented in the install guide.

---

## 9. Discoverability

- **Searchable API table** on RTD (the table in §5 above).
- `rpm.help("lmrobdetMM")` returns the same docstring whether the user types R name or Python name.
- `dir(rpm)` returns the flat re-export list — sorted, no `_private` noise.
- Tab-completion in Jupyter/IPython surfaces submodules + functions cleanly because of the dataclass + flat re-export design.
- Every wrapper's `See Also` section in the docstring cross-references related wrappers (e.g. `lmrobdet_mm` ↔ `lmrobdet_dcml` ↔ `step_lmrobdet`).

---

## 10. Notebook / Jupyter ergonomics

- **Rich `_repr_html_`** on every result dataclass: in Jupyter, a `fit` cell renders as an HTML table mirroring R's `summary()`.
- `_repr_html_` on `SummaryTable`: full HTML table with coefficient names, estimates, std errs, t-stats, p-values.
- `fit._repr_mimebundle_` returns both HTML and plain text so non-Jupyter contexts also work.

---

## 11. Performance ergonomics

- `rpm.set_n_jobs(n)` — for the few wrappers that internally fan out (`pyinit` candidate evaluation, `KurtSDNew` random directions), control R-side parallelism without touching `options()`.
- `rpm.bench.timer(fit)` — quick wrapper around `timeit`, returns Python and R time separately so users see bridge overhead.
- **Lazy R startup is observable**: `rpm.r_started()` returns `True`/`False`; first wrapper call prints a one-line status message if `RPM_VERBOSE=1`.

---

## 12. Tutorial structure (Phase 5)

Three tutorial notebooks targeting three personas:

| Notebook | Persona | Content |
|----------|---------|---------|
| `tutorials/01_quickstart.ipynb` | "I want robust regression for tomorrow's analysis" | 5-minute tour: load data → `lmrobdet_mm` → summary → plot residuals → predict |
| `tutorials/02_from_textbook.ipynb` | "I'm reading Maronna et al. and want to reproduce Ch 5" | Chapter-by-chapter walkthrough using the textbook datasets; explicitly compares to base R `lm` |
| `tutorials/03_from_R.ipynb` | "I have R scripts I want to port" | Side-by-side R / Python code blocks; references the §5 name table; covers formula handling and `data()` → `datasets` |

Each notebook ends with the reproducibility cell (versions of everything) — see `docs/documentation_standards.md §8`.

---

## 13. What this design rules out

- **No magic.** The user never has to call `set_conversion`, `importr`, or any rpy2 function directly.
- **No silent fallbacks.** If R is missing, every wrapper raises `RobStatTMSetupError` with the install command — never returns garbage or a degraded "pure-Python emulation".
- **No mutation.** Results are frozen. Mutating wrapper outputs is an anti-pattern; we don't accommodate it.
- **No global state outside of seed + lazy R handle.** No package-level "current control object" or "current dataset" globals.

---

## 14. Open questions

1. Should `rpm.lmrobdet_mm` accept an existing rpy2 `Formula` object directly? Recommendation: **yes**, for power users — type-check `isinstance(formula, ro.Formula)`.
2. Should we ship a `%load_ext robstatm_py` Jupyter extension that pre-warms R? Recommendation: **defer** to v0.2.0.
3. Should `__repr__` truncate long coefficient vectors? Recommendation: **yes** — show first 5, last 5, with "…" middle marker (numpy `printoptions`-aware).
4. Should `to_pandas()` be standard or `to_polars()` also? Recommendation: pandas standard; polars in v0.2.0.

All four are tracked as open in `project_memory/blockers.md` if not resolved before Bonding.
