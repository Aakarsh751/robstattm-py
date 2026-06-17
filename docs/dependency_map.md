# Dependency Map — RobStatTM and Friends

**Audited against:** `robstattm/RobStatTM-master/` (RobStatTM 1.0.12, dated 2025-03-11)
**Method:** read `DESCRIPTION`, `NAMESPACE`, and `grep` for `::` namespace calls and `library()` / `require()` in `R/*.R`.

---

## 1. RobStatTM declared dependencies (`DESCRIPTION`)

```
Depends:  R (>= 3.5.0)
Imports:  stats, pyinit, rrcov, robustbase
Suggests: R.rsp
LinkingTo: (none — C/Fortran built in-tree under src/)
```

`NAMESPACE` declares only `import(stats)` — everything else is reached through `::` qualified calls (good, because it lets us see exactly where each import is used).

---

## 2. Where each external R package is actually used

Grep over `R/*.R` produces:

| External R package | Used inside RobStatTM at | Why |
|--------------------|--------------------------|-----|
| **`pyinit`** | `DCML.R:165`, `DCML.R:333` | Peña–Yohai highly robust initial estimator for `lmrobdetDCML` (and indirectly for `lmrobdetMM` when initialization defers to pyinit) |
| **`robustbase`** | `BYlogreg.R:86`, `WBYlogreg.R:87`, `WMLlogreg.R:80` (all three: `covMcd` for initial covariance); `lmrob.MM.R:962` (uses `robustbase::lmrob` to fit a τ-correction model); `lmrobdet.R` lines 259/345/1007/1093 (`robustbase::robMD` — robust Mahalanobis distance for leverage diagnostics) | MM-fit τ correction and robust leverage diagnostics for `lmrobdetMM` / `lmrobM`; MCD initial covariance for GLM wrappers |
| **`rrcov`** | `RobPCA_SM.R:47` (`rrcov::PcaLocantore`) | Spherical-PCA initialization for `pcaRobS` |
| **`stats`** | everywhere | Base R linear algebra, `lm.fit`, distribution functions |

---

## 3. Function → required R packages (transitive)

For each target wrapper, the R package(s) that **must be installed** to make the underlying R call succeed:

| Wrapper | RobStatTM | pyinit | robustbase | rrcov | pense | GSE | Notes |
|---|:-:|:-:|:-:|:-:|:-:|:-:|---|
| `locScaleM` | ✔ |   |   |   |   |   | Pure RobStatTM (`MLocDis.R`) |
| `mScale` | ✔ |   |   |   |   |   | Pure RobStatTM (`Multirobu.R`) |
| `lmrobM` | ✔ |   | ✔ |   |   |   | Uses `robMD` for leverage |
| `lmrobdetMM` | ✔ | ✔* | ✔ |   |   |   | `pyinit` only when `initial="pyinit"` (default for moderate-p); `robustbase` for τ-correction + `robMD` |
| `lmrobdet.control` | ✔ |   |   |   |   |   | Pure parameter object |
| `lmrobdetDCML` | ✔ | ✔ | ✔ |   |   |   | Hard pyinit dependency at `DCML.R:165` and `:333` |
| `step.lmrobdet` | ✔ | ✔* | ✔ |   |   |   | Same as lmrobdetMM |
| `pyinit` | ✔ | ✔ |   |   |   |   | Wrapping the `pyinit::pyinit()` API directly |
| `rob.linear.test` | ✔ | ✔* | ✔ |   |   |   | Refits MM models internally |
| `covRobMM` | ✔ |   | ✔ |   |   |   | M-iteration; uses robustbase Mahalanobis utilities |
| `covRobRocke` | ✔ |   |   |   |   |   | Pure RobStatTM `Multirobu.R` |
| `KurtSDNew` | ✔ |   |   |   |   |   | Pure RobStatTM |
| `pcaRobS` | ✔ |   |   | ✔ |   |   | rrcov::PcaLocantore for SP-init |
| `BYlogreg` | ✔ |   | ✔ |   |   |   | covMcd initial |
| `WBYlogreg` | ✔ |   | ✔ |   |   |   | covMcd initial |
| `WMLlogreg` | ✔ |   | ✔ |   |   |   | covMcd initial |
| **Stretch** `pense` |   |   |   |   | ✔ |   | Independent package |
| **Stretch** `GSE` |   |   |   |   |   | ✔ | Independent package |
| **Stretch** `TSGS` |   |   |   |   |   | ✔ | Lives in same `GSE` package |

`*` = optional but typical default.

### 3.1 Minimum install for each phase

- **Phase 1 (locScaleM / mScale):** `RobStatTM` only.
- **Phase 2 (regression):** `RobStatTM`, `pyinit`, `robustbase`.
- **Phase 3 (covariance + PCA):** `RobStatTM`, `robustbase`, `rrcov`.
- **Phase 6 stretch (`pense`):** `pense` (CRAN). Brings its own C++ code.
- **Phase 6 stretch (`GSE` / `TSGS`):** `GSE` (CRAN).
- **Phase 6 stretch (GLM `*logreg`):** `RobStatTM` + `robustbase`.

### 3.2 Full union of R packages

The package's `check_setup()` utility should verify these CRAN packages are importable:

```
RobStatTM   pyinit   robustbase   rrcov   pense   GSE
```

Plus implicit transitive R deps (each will be pulled in by `install.packages`): `MASS`, `Matrix`, `Rcpp` (for pense), `mvtnorm`, `numDeriv`, `pcaPP`, `quantreg` (varies by version).

---

## 4. Python-side dependencies

From the proposal §12 and the existing `robstattm/python/requirements.txt`:

| Package | Version pin | Why |
|---------|-------------|-----|
| `rpy2` | `>= 3.6.6` | Conversion context API (`set_conversion(default_converter)`) lives in 3.6+ |
| `numpy` | `>= 1.20` | Standard input type |
| `pandas` | `>= 1.2` | DataFrame conversion via `pandas2ri` |
| `scipy` | `>= 1.6` | Distribution / linalg helpers for Python-side validation utilities |
| `matplotlib` | `>= 3.3` | Default Python plotting |
| `plotnine` | latest | ggplot-style fallback for plots (proposal §3) |
| `statsmodels` | `>= 0.12` | Classical-baseline benchmarks |
| `scikit-learn` | latest | Classical-baseline benchmarks |
| `pytest` | `>= 7` | Test runner |
| `pytest-cov` | latest | Coverage gate (≥ 90%) |
| `sphinx` + `numpydoc` + `sphinx-rtd-theme` | latest | Docs build |
| `nbformat`, `nbconvert` | `>= 5/6` | Tutorial notebooks rendered in CI and on RTD |

Dev-only extras: `build`, `twine`, `ruff` (or `flake8`+`black`), `mypy`.

---

## 5. Version constraints

| Component | Minimum | Tested matrix | Notes |
|-----------|---------|---------------|-------|
| R | 4.3 | 4.3, 4.4, 4.5 (CI) | Proposal §12, §13 |
| Python | 3.10 | 3.10, 3.11, 3.12 (CI) | rpy2 3.6 dropped 3.8/3.9 |
| RobStatTM (R) | 1.0.12 | 1.0.12 (vendored) | Latest CRAN snapshot at proposal time |
| pyinit (R) | 1.1.1 | latest CRAN | Windows binary historically lags |
| robustbase (R) | 0.99 | latest CRAN | Very stable |
| rrcov (R) | 1.7 | latest CRAN |  |
| pense (R) | 2.2 | latest CRAN | Rcpp + Eigen; ~30 MB |
| GSE (R) | 4.2 | latest CRAN |  |
| rpy2 | 3.6.6 | 3.6, 3.7 (CI) |  |

The package itself enforces the minimums at runtime in `check_setup()`; CI verifies the matrix.

---

## 6. Compatibility risks (with mitigations)

| Risk | Severity | Mitigation |
|------|----------|------------|
| **`pyinit` Windows binary** sometimes lags CRAN source releases | High for Phase 2 | Document fallback: install from source via Rtools; CI uses macOS + Linux for `pyinit`-dependent jobs first; skip `pyinit`-requiring tests on Windows with a clearly emitted `pytest.skip` when unavailable |
| **`pense` install size and compile time** | Medium | Make stretch — not required for Phase 1–5 deliverables; cache CI build artifacts |
| **`rpy2` 3.6 conversion context lost across Jupyter async boundaries** | Medium | Patch at package import: `from rpy2.robjects.conversion import set_conversion; set_conversion(default_converter + numpy2ri.converter + pandas2ri.converter)` |
| **R 4.5 deprecations / behavior shifts** between matrix tiers | Low-Medium | CI matrix forces all three R minors; lock RobStatTM upstream to 1.0.12 even if newer CRAN appears mid-project |
| **CRAN package version drift during the GSoC window** | Low | Use `renv`-style lockfile in CI (`renv.lock`) recording exact versions per CI run |
| **`rrcov::PcaLocantore` API change** | Low | If it changes, `pcaRobS` breaks; pin `rrcov` in lockfile |
| **Conda vs. pip for rpy2 on Windows** | Medium | Document conda-forge path as recommended on Windows; pip path on Linux/macOS (proposal §13) |
| **C/Fortran toolchain availability** for source installs of `pyinit`, `pense` | Medium | Pre-built wheels on CI runners; user docs recommend Rtools on Windows |

---

## 7. Installation requirements (user-facing summary, draft)

This is the language the eventual install guide must convey (drafted here for review):

> `robstatm-py` requires:
> - Python ≥ 3.10
> - R ≥ 4.3 with the following CRAN packages installed: `RobStatTM`, `pyinit`, `robustbase`, `rrcov`. Stretch wrappers add `pense` and `GSE`.
> - `rpy2 ≥ 3.6.6` on the Python side.
>
> After installing, run `python -c "import robstatm_py; robstatm_py.check_setup()"` to verify your R environment.

---

## 8. Open questions

1. Should `check_setup()` **auto-install** missing CRAN packages? Recommendation: **No** — print the exact `install.packages(c(…))` command instead. Avoids surprising network calls on import.
2. Should we vendor a minimal `renv.lock` to pin exact CRAN versions used in CI? **Recommendation: yes** for reproducibility.
3. Mentor decision needed on whether `pense` / `GSE` make it into the v0.1.0 PyPI release or wait for v0.2.0. Tracked in `project_memory/blockers.md`.
