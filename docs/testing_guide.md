# RobStatTM-Py Testing Guide

**Audience:** developers, reviewers, and mentors who want to understand *how* this package is tested, *what* each layer checks, and *what the outputs mean*.

**Last verified:** 2026-06-17 on Windows (R 4.5.2, PowerShell).

---

## 1. The core idea

RobStatTM-Py is **not** a pure-Python reimplementation of robust statistics. Every public function is a thin **rpy2 wrapper** around the original R package `RobStatTM`.

Therefore the golden rule of testing is:

> **Python wrapper output must match a direct R call on the same data, with the same control object and the same random seed — field by field, with zero numerical tolerance.**

When a test passes, it means:

- You called `rpm.lmrobdet_mm(...)` (or similar) in Python.
- The test also ran `RobStatTM::lmrobdetMM(...)` in **embedded R** (via rpy2, same process).
- Every compared number is **bit-identical** (`atol=0`, `rtol=0`).

When a test fails, it usually means the wrapper dropped an argument, mis-converted a field name, lost the fit’s control object on refit, or mishandled an edge case — not that “statistics looks wrong.”

---

## 2. How R is used in tests

Tests do **not** compare Python to hand-written expected values in a CSV. They compare Python to **live R** inside pytest.

### 2.1 Embedded R via rpy2

When pytest imports `robstatm_py`, the first wrapper call starts an **embedded R interpreter** inside the Python process (`src/robstatm_py/_r.py`). Tests use the same bridge as production code:

| Helper | Location | Purpose |
|--------|----------|---------|
| `r()` | `_r.py` | Returns rpy2 `robjects`; installs numpy/pandas conversion once |
| `r_pkg("RobStatTM")` | `_r.py` | Cached `importr("RobStatTM")` |
| `rcall(rfun, ...)` | `_r.py` | Call R function; translate errors to `RobStatTMRError` |
| `R` fixture | `tests/conftest.py` | Shortcut: `R("coef(fit_r)")` evaluates R strings in tests |
| `set_seed(n)` | `robstatm_py` | Sets **both** NumPy and R RNG (`set.seed(n)`) |

Typical strict-tier test pattern:

```python
@needs_r
def test_coefficients_match_r(R):
    # --- R reference side ---
    R("library(RobStatTM); data(mineral)")
    R("fit_r <- lmrobdetMM(zinc ~ copper, data=mineral)")

    # --- Python wrapper side ---
    py = rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())

    # --- Compare ---
    r_coef = np.asarray(R("coef(fit_r)"), dtype=float)
    np.testing.assert_array_equal(py.coefficients, r_coef)
```

This is the same philosophy as the parity check you might run manually — it is just automated across hundreds of cases.

### 2.2 Why embedded R instead of a separate R session?

Both approaches use real R. Embedded R is chosen because:

- Data moves as pandas DataFrames → R data.frames without file round-trips.
- CI runs one job: `pytest` with R installed.
- Strict parity checks stay fast enough for 500+ tests.

A separate `Rscript` subprocess would still be “using R,” but would be slower and harder to keep in sync with pandas preprocessing.

### 2.3 Prerequisites

```powershell
# Windows example (required before rpy2 works)
$env:R_HOME = "C:\Program Files\R\R-4.5.2"
$env:PATH = "C:\Program Files\R\R-4.5.2\bin\x64;" + $env:PATH

cd robstatm-py
pip install -e ".[dev]"
python -c "import robstatm_py as rpm; rpm.check_setup()"
```

**Required R packages:** `RobStatTM`, `robustbase`, `rrcov`, `pyinit`  
**Optional (stretch tests skip if missing):** `pense`, `GSE`

Tests marked `@needs_r` are **skipped** (not failed) when R or RobStatTM is unavailable.

---

## 3. Tolerance tiers

Defined in `docs/validation_strategy.md`:

| Tier | atol / rtol | When used |
|------|-------------|-----------|
| **Strict** (default) | `0.0` / `0.0` | All wrapper vs R comparisons in `tests/` and `exploration/` |
| Stable | `1e-12` | Rare rpy2 coercion paths; must be documented on the assertion line |
| Algorithmic | `1e-8` / `1e-6` | Native-Python reimplementations only (future stretch) |
| Plot | image norm `1e-3` | Figure regression (not yet CI-gated) |

**Strict tier helpers** (`tests/conftest.py`):

- `assert_scalar_equal(py, r_val)` — scalars; `NaN == NaN` counts as equal
- `assert_array_equal(py, r_val)` — wraps `np.testing.assert_array_equal`
- `assert_r_equal_dataclass(py_obj, r_list, field_map)` — field-by-field on dataclasses

---

## 4. Test layers (overview)

```
                    ┌─────────────────────────────────────┐
                    │  Human confidence (not CI gates)     │
                    │  verify.py, smoke scripts, examples  │
                    └─────────────────────────────────────┘
                                      │
                    ┌─────────────────────────────────────┐
                    │  Notebooks (13) — execution only       │
                    │  tests/test_notebooks.py             │
                    └─────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┴─────────────────────────────┐
        │                                                             │
┌───────▼────────┐                                          ┌────────▼────────┐
│  STRICT TIER   │                                          │  EXPLORATION    │
│  tests/        │                                          │  exploration/   │
│  572 tests     │                                          │  173 tests      │
│  CI gate       │                                          │  R-parity too   │
└────────────────┘                                          └─────────────────┘
        │                                                             │
        └─────────────────────────────┬─────────────────────────────┘
                                      │
                    ┌─────────────────▼───────────────────┐
                    │  Docs validator                      │
                    │  docs/scripts/validate_docs.py       │
                    └─────────────────────────────────────┘
```

**Current counts** (2026-06-17, `RPM_SKIP_NOTEBOOKS=1`):

| Layer | Location | Tests | Runtime (approx.) | CI gate? |
|-------|----------|-------|-------------------|----------|
| Strict unit | `tests/` | **572 passed**, 14 skipped | ~2 min 20 s | Yes |
| Exploration | `exploration/` | **173 passed** | ~1 min 7 s | Optional / local |
| **Combined** | `tests/` + `exploration/` | **745 passed**, 14 skipped | ~3 min 14 s | Strict part yes |
| Notebooks | `tests/test_notebooks.py` | 14 parametrized runs | ~4–5 min extra | Yes (unless skipped) |
| Doc examples | `docs/scripts/validate_docs.py` | 22+ wrapper pages | ~30 s | Manual / docs CI |

Set `RPM_SKIP_NOTEBOOKS=1` to skip the 14 notebook executions during fast loops.

---

## 5. Strict tier (`tests/`) — the CI gate

**Purpose:** Every shipped wrapper, S3 method, dataset loader, and ergonomic API must match R on textbook and representative inputs. These tests **block releases**.

### 5.1 Directory map

| Directory / file | What it verifies | Example outputs compared |
|------------------|------------------|--------------------------|
| `tests/univariate/` | `loc_scale_m`, `m_scale` | `mu`, `std.mu`, `disper`; M-scale scalar |
| `tests/regression/` | MM, DCML, M, step, pyinit, linear test, drop1, controls | `coefficients`, `scale`, `residuals`, `fitted.values`, `cov`, RFPE tables |
| `tests/covariance/` | MM, Rocke, dispatcher, classic, fastmve, kurt | `center`, `cov`, `dist`, `cor`; `na_action` paths |
| `tests/pca/` | `pca_rob_s`, `prcomp_rob` | `sdev`, `rotation`, `eigvec`, `propex` |
| `tests/glm/` | BY, WBY, WML | `coefficients`, `standard.deviation`, `fitted.values`, separation errors |
| `tests/psi/` | ρ, ψ, ψ′ for 6 families × efficiencies | Elementwise arrays |
| `tests/datasets/` | 20 native loaders + `datasets.load()` | DataFrame shape, column names, values vs R |
| `tests/external/` | `pense`, `pense_cv`, `gse`, `tsgs` | Coef paths, S4 slots vs R accessors |
| `tests/extra/` | Gaps not covered elsewhere | No-intercept formulas, multi-predictor X/y, custom control on lmrobM |
| `tests/plot/` | Native plotting suite (`robstatm_py.plot`) | Return types, `ax=`, themes, backend resolution, **no-refit guard** (R-free) |
| `tests/test_ui_ergonomics.py` | `help()`, `to_dict()`, pickle, X/y API, plot shortcuts | Structure / round-trip, not always numeric |
| `tests/test_compat_r.py` | R-name aliases (`lmrobdetMM`, etc.) | Import and call paths |
| `tests/test_notebooks.py` | All `notebooks/**/*.ipynb` | **No cell errors** (outputs not numerically asserted) |

### 5.2 What “output” means in strict tests

Each wrapper returns a **frozen Python dataclass** (e.g. `LmrobdetMMResult`). Tests compare selected attributes to R `$` components:

| Python attribute | Typical R field | Comparison |
|------------------|-------------------|------------|
| `fit.coefficients` | `coef(fit)` or `fit$coefficients` | `assert_array_equal` |
| `fit.scale` | `fit$scale` | `assert_scalar_equal` |
| `fit.residuals` | `fit$residuals` | `assert_array_equal` |
| `step.anova_rfpe` | `step$anova$RFPE` | `assert_array_equal` |
| `cov.center`, `cov.cov` | `fit$center`, `fit$cov` | `assert_array_equal` |

**S3 methods** (summary, predict, hatvalues, drop1, rfpe) are tested by refitting in R-space and comparing the recomputed tables — including the case where the user passed a **custom `lmrobdet_control`** (regression bug D-021).

### 5.3 Validation matrix (cases 1–11)

`docs/validation_strategy.md` defines 11 standard cases per wrapper (textbook golden, clean synthetic, contaminated, high-dimensional, bad inputs, seed repeatability, etc.). Strict tests map onto these across modules — not every file lists case numbers, but coverage is tracked in `docs/coverage_matrix.md`.

### 5.4 Notable strict-tier bugs found by testing

| Bug | How tests caught it | Fix |
|-----|---------------------|-----|
| Dot formula `Y ~ .` crashed | `tests/regression/test_dot_formula.py` | `coef_names_for()` with model.matrix |
| Custom control lost on refit | `tests/regression/test_lmrobdet_mm_methods.py` | Store `_r_control`, reuse in S3 refits |
| `cov_classic(na_action="omit")` never forwarded | `tests/covariance/test_covariance.py` | Pass `na.action=` to R |
| WBY on separable data opaque error | `tests/glm/test_logreg.py` + exploration | Raise `RobStatTMRError` (B-009) |
| MASS attach masked `huber` | `tests/datasets/test_load_crosspackage.py` | `datasets.load` without attaching packages |

---

## 5b. Plotting tests (`tests/plot/`) — native suite, R-free

**Purpose:** The native plotting suite (`robstatm_py.plot`, decision D-023) is a
*rendering* layer, not a numeric one — its inputs are the already-validated
arrays on the result dataclasses. So these tests check the **plotting contract**,
not numbers, and they run **without R** (a duck-typed `fake_fit`/`fake_cov`/`fake_pca`
fixture carries the same arrays a real fit exposes).

| File | What it verifies |
|------|------------------|
| `tests/plot/conftest.py` | R-free fixtures; forces the headless `Agg` backend; isolates the global theme per test |
| `tests/plot/test_style.py` | `PlotStyle` defaults, named themes, override order, frozen-ness |
| `tests/plot/test_backends.py` | `backend="auto"` → native/`r` fallback, error paths, `r_kwargs` whitelist |
| `tests/plot/test_regression_diagnostics.py` | return types (`Axes`/`Figure`), `ax=` honored, highlight/labels/annotate, save, **no-refit guard**, no implicit `plt.show()` |
| `tests/plot/test_multivariate.py` | distance-distance / scree / scores / loadings / biplot / cov-heatmap; outlier flagging; too-few-components guard |
| `tests/plot/test_univariate.py` | `location_scale`, `scatter_with_fit`, `compare_fits` |

**Two contract guarantees the tests lock in:**

1. **No-refit guard.** Native renderers must never touch the R bridge. The tests
   monkeypatch `robstatm_py._r.{r,r_pkg,rcall}` to raise, then draw every native
   plot — if any plot calls into R, the test fails. (`backend="r"` is the only
   path allowed to refit.)
2. **Composability.** Passing `ax=` must draw into that Axes and create **no**
   new figure; the library must not call `plt.show()` unless `show=True`.

**Skips cleanly without the extra:** every file starts with
`pytest.importorskip("matplotlib")`, so a checkout without `[plots]` installed
just skips this layer instead of erroring.

```bash
# fast, R-free — runs anywhere matplotlib is installed
MPLBACKEND=Agg python -m pytest tests/plot/ -q       # 63 passed
```

The `backend="r"` (Path-A) shortcuts are additionally exercised **with** R in
`tests/test_ui_ergonomics.py::TestDiagnosticPlots` (native Axes/Figure default +
PNG via `backend="r"`).

---

## 6. Exploration tier (`exploration/`) — broader workflows

**Purpose:** Exercise realistic **Python-native workflows** (synthetic data, pandas pipelines, sklearn imports) that go beyond the minimal textbook paths in `tests/`. Exploration tests **still use strict R parity** — they are not “soft” tests.

**Location:** `exploration/` (separate from `tests/` so new scenarios can be added without expanding the CI gate until promoted).

**Shared infrastructure:**

- `exploration/conftest.py` — re-exports `R`, `needs_r`, assert helpers from `tests/conftest.py`
- `exploration/_synth.py` — data generators + `push_to_r` / `reval` / `rm_r` for R globalenv plumbing

### 6.1 Module breakdown

| Module | Tests | What it does | Typical outputs verified |
|--------|-------|--------------|--------------------------|
| `test_synthetic_pipelines.py` | 42 | NumPy-generated data → every wrapper family | Full numeric fields (coef, scale, residuals, cov, loadings, deviances, S4 slots) |
| `test_combinatorial_matrix.py` | ~45 | Dataset × family × estimator grids | Spot parity on mineral/stackloss/shock; method chains |
| `test_data_ingress.py` | 7 | CSV, sklearn, cross-package load, pandas wrangling | Coef/scale after real preprocessing pipelines |
| `test_edge_cases.py` | 19 | NaN, rank deficiency, separation, bad args | Clean Python errors **or** bit-parity where R succeeds |
| `test_regression_exploration.py` | 10 | Extra regression workflows | R parity on alternate formulas/datasets |
| `test_multivariate_exploration.py` | 10 | Cov/PCA workflows | center, cov, distances |
| `test_dataset_workflows.py` | varies | Textbook dataset combinations | End-to-end fits |
| `test_helpers_and_glm.py` | 14 | GLM + helper paths | Coef, fitted values |

Full scenario catalog: **`exploration/DATA_PIPELINES.md`**.

### 6.2 Synthetic pipeline example (what happens step by step)

1. **Generate data in Python** with `numpy.random.default_rng(seed)` — fixed array regardless of R RNG.
2. **Push the same frame to R** via `push_to_r(df, "rpm_data")`.
3. **Call Python wrapper** — e.g. `rpm.lmrobdet_mm("y ~ x0 + x1", data=df)`.
4. **Call equivalent R** — e.g. `reval("lmrobdetMM(y ~ x0 + x1, data=rpm_data)")`.
5. **Compare** `coefficients`, `scale`, `residuals`, `fitted.values`, `cov` with `assert_array_equal`.

For **stochastic** estimators (MM, Rocke, pense), both sides call `rpm.set_seed(n)` and `set.seed(n)` before fitting so the R random stream matches.

### 6.3 Data ingress example (what it proves)

Models a real analyst workflow:

```text
sklearn.load_diabetes() → inject outliers → pandas DataFrame → rpm.lmrobdet_mm(...)
                                      ↓ same frame pushed to R
                              lmrobdetMM(...) in R
                                      ↓
                              coefficients must match exactly
```

This proves parity survives **CSV round-trips, merges, dropna, astype**, not just pristine `datasets.mineral()`.

### 6.4 Edge-case example (two kinds of “output”)

| Situation | Expected test outcome |
|-----------|------------------------|
| NaN in numeric input | `pytest.raises(ValueError)` **before** rpy2 (Python validation) |
| Rank-deficient design | R returns `NaN` for non-identifiable coef; Python must match **exactly** |
| WBY on perfectly separable data | `pytest.raises(RobStatTMRError, match="usable fit")` after B-009 fix |
| `p > n` covariance | `RobStatTMRError` with clear message |

### 6.5 Promotion policy

Passing exploration cases can **graduate into `tests/`** when they are stable, fast, and deterministic. Strongest candidates: full-field synthetic parity (scenarios A.5–A.16 in `DATA_PIPELINES.md`). See `exploration/TESTING.md`.

---

## 7. Extra strict tests (`tests/extra/`)

Added to cover API shapes the core regression tests did not stress:

| File | Focus |
|------|-------|
| `test_regression_extra.py` | No-intercept formulas, multi-predictor `(X, y)`, lmrobM headline kwargs |
| `test_covariance_extra.py` | Additional cov argument combinations |
| `test_univariate_glm_extra.py` | Univariate/GLM parameter sweeps |
| `test_psi_invtr2_extra.py` | ψ-family and INVTR² edge parameters |
| `test_compat_help_extra.py` | Help system and alias coverage |
| `test_ergonomics_extra.py` | Result method chains, repr, conversions |

These run as part of `pytest tests/` (strict tier).

---

## 8. Notebook testing

**File:** `tests/test_notebooks.py`  
**Policy:** D-019 in `project_memory/decisions.md` — a notebook is “done” only if it executes without error in CI.

**How it works:**

1. Discovers all `notebooks/**/*.ipynb` (14 notebooks).
2. Executes each top-to-bottom with **nbclient** (600 s timeout).
3. Asserts **no `CellExecutionError`**.

**What it does *not* check:**

- Pixel-perfect figure comparison (no pytest-mpl baselines yet).
- Numeric parity inside notebook cells (gallery notebooks often print `True` from inline `np.array_equal` checks, but CI only requires clean execution).

**Notebooks covered:**

| Notebook | Role |
|----------|------|
| `tutorials/01_quickstart.ipynb` | End-user quickstart |
| `tutorials/02_outlier_detection.ipynb` | Multivariate outliers |
| `tutorials/03_from_R.ipynb` | R → Python porting guide |
| `tutorials/aakarsh_test.ipynb` | Scratch / experiments |
| `ch5_mineral.ipynb`, `ch6_wine.ipynb` | Chapter figures |
| `external_demo.ipynb` | pense / GSE / TSGS |
| `gallery/ch2_*.ipynb` … `ch7_*.ipynb`, `vignette.ipynb` | Example-script reproductions |
| `ui_demo.ipynb` | API tour |

---

## 9. Documentation testing

### 9.1 Runnable examples (`docs/examples/*.py`)

23 hand-authored Python scripts — one per major wrapper. Each is a minimal runnable demo.

### 9.2 Doc validator (`docs/scripts/validate_docs.py`)

For every page in `docs/api/wrappers/*.md`:

| Check | Pass criterion |
|-------|----------------|
| Import | `from robstatm_py import <name>` resolves |
| Example | Python block under `## Example` runs without exception |
| Returns table | Every dataclass field documented; no phantom fields |
| R examples (if present) | Paired `.R` files execute via `Rscript` |

**Output:** `ALL OK (N/N)` or a per-page failure report; exit code non-zero on failure.

### 9.3 Sphinx build

```bash
python -m sphinx -b html docs docs/_build/html -W
```

`-W` treats warnings as errors. Docs build is **R-free** (no autodoc import of live wrappers).

---

## 10. Manual / ad hoc checks

Not collected by pytest; useful before demos or mentor reviews.

| Tool | Command | What you see |
|------|---------|--------------|
| **verify.py** | `python verify.py --quick` | Smoke: every wrapper family runs; `[OK]` lines |
| **verify.py full** | `python verify.py` | Smoke + runs strict pytest subset |
| **Coverage matrix** | `python verify.py --coverage` | R↔Python wrapper inventory table |
| **Smoke scripts** | `python tests/_smoke_step_rlt.py` | step + linear test parity printout |
| **Playground** | `python exploration/run_playground.py all` | 10 interactive scenarios |

---

## 11. How to run everything

```powershell
# Environment (Windows)
$env:R_HOME = "C:\Program Files\R\R-4.5.2"
$env:PATH = "C:\Program Files\R\R-4.5.2\bin\x64;" + $env:PATH
cd C:\ProfDM_Rproject\robstatm-py

# Fast CI loop (no notebooks)
$env:RPM_SKIP_NOTEBOOKS = "1"
python -m pytest tests/ -q

# Exploration only
python -m pytest exploration/ -q

# Full numeric suite
python -m pytest tests/ exploration/ -q

# Include notebooks (~5 min longer)
Remove-Item Env:RPM_SKIP_NOTEBOOKS -ErrorAction SilentlyContinue
python -m pytest tests/ -q

# Docs
python docs/scripts/validate_docs.py
python -m sphinx -b html docs docs/_build/html -W

# Human-readable smoke
python verify.py --quick
```

---

## 12. Interpreting results

### 12.1 pytest

```
572 passed, 14 skipped in 139s     # strict (notebooks skipped)
173 passed in 67s                  # exploration
745 passed, 14 skipped in 194s     # combined
```

- **passed** — assertion succeeded (numeric match or expected exception).
- **skipped** — R unavailable, optional package missing (`pense`/`GSE`), or `RPM_SKIP_NOTEBOOKS=1`.
- **failed** — mismatch vs R, unexpected exception, or notebook cell error. Read the `assert_array_equal` diff or `RobStatTMRError` traceback.

### 12.2 Strict parity success example

Stackloss stepwise with custom control (manual parity script):

```
Coefficients: [-0.080472  0.081861  0.054461 -0.073558]  # Python == R
RFPE:         [0.276333]
Scale:        0.19783921079253777
OVERALL BIT-IDENTICAL: True
```

### 12.3 What tests do *not* guarantee

- Identical **plot pixels** across machines (figures are visual-only in CI).
- Reproduction of **out-of-scope** example scripts (time-series inline R, `robustvarComp`, etc.) — see `notebooks/README.md`.
- Performance benchmarks (Phase 4 notebook not yet a hard gate).
- Multi-platform parity on every OS×R version (CI matrix authored but not fully wired at monorepo root).

---

## 13. Randomness cheat sheet

| Data source | Seed both sides? |
|-------------|------------------|
| Built-in datasets (`mineral`, `stackloss`) | Usually no (deterministic fits) |
| Stochastic estimators (MM, Rocke, pense) | **Yes** — `rpm.set_seed(n)` + R `set.seed(n)` |
| Python-synthesized arrays | Data fixed by `default_rng`; seed estimators separately |
| Peña–Yohai init only | Often reproducible without seed (documented in examples) |

Always use **fixed integer seeds** in tests — never `time.time()` or unseeded RNG.

---

## 14. Related documents

| Document | Content |
|----------|---------|
| `docs/validation_strategy.md` | Formal tolerance policy, cases 1–11, CI plan |
| `docs/quality_gates.md` | Per-wrapper Definition of Done checklist |
| `docs/coverage_matrix.md` | Authoritative wrapper ↔ test file map |
| `exploration/TESTING.md` | Short command cheat sheet |
| `exploration/DATA_PIPELINES.md` | Full synthetic/ingress/edge catalog |
| `docs/notebook_plan.md` | Notebook CI policy (D1–D4) |
| `project_memory/progress_log.md` | Session history of test campaigns |
| `project_memory/decisions.md` | D-021, D-022, D-019 testing decisions |

---

## 15. Quick FAQ

**Q: Are we testing Python or R?**  
A: Both. Python wrappers are tested **against R** as the reference implementation.

**Q: Why do tests use `ro.r("...")` strings?**  
A: Convenience for the R reference side in tests. Production wrappers prefer typed `rcall(r_pkg("RobStatTM").lmrobdetMM, ...)`.

**Q: What is the difference between `tests/` and `exploration/`?**  
A: Same strict numeric standard; `tests/` is the CI gate, `exploration/` is broader scenarios that may later be promoted.

**Q: If exploration passes but strict fails, can we release?**  
A: No. Only `tests/` (and agreed CI jobs) gate releases.

**Q: How do I add a test for a new wrapper?**  
A: Follow `templates/test_wrapper.py.tmpl`, use `@needs_r`, compare every numeric field to R with `assert_array_equal`, run `pytest tests/<module>/ -q`.
