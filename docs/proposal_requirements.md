# Proposal Requirements — distilled

**Source:** `docs/gsoc2026_proposal/RobStatTM-Py GSOC2026 Proposal.tex` (v4, submitted 2026-03-30)
**Mentors:** R. Douglas Martin (primary), Matias Salibian-Barrera, Brian G. Peterson
**Project size:** Large, 350 hours, 22 weeks, May 25 – Nov 2, 2026 (coding window)

---

## 1. Core deliverables (verbatim from proposal §§3, 7, 10, 11)

1. **Pip-installable Python package** `pip install robstatm-py`.
2. **`rpy2` wrapper layer** exposing the full proposal §4 target function set.
3. **Bit-for-bit numerical equivalence** with R: every wrapper field-by-field matches a direct R call (the metric is `max_i |y_i^Py − y_i^R| == 0`).
4. **`pytest` validation suite with ≥ 90% coverage**, field-by-field against R.
5. **Sphinx + ReadTheDocs API documentation**, NumPy-style docstrings modeled on the RobStatTM R man pages.
6. **Tutorial Jupyter notebooks** reproducing key examples from Maronna et al. (2019) Chapters 2, 5, 6.
7. **Comparative benchmark notebook**: native R session vs. `rpy2` wrappers vs. classical Python baselines (`scikit-learn`, `statsmodels`) on synthetic contaminated Gaussian data ($n \in \{100, 1000, 10000\}$, $p \in \{5, 20, 50\}$) and real datasets (`mineral`, `wine`, `bus`).
8. **Plot reproduction**: R-generated diagnostics where possible; otherwise `matplotlib` / `plotnine` recreations that mirror the R originals closely.
9. **CI/CD on GitHub Actions**: Linux/macOS/Windows × R 4.3/4.4/4.5 matrix.
10. **PyPI release** (sdist + wheel) plus GitHub direct-install path.
11. **Installation guide and `robstatm_py.check_setup()` utility** for R-environment validation.

---

## 2. Architectural constraints (proposal §7)

- Inputs accepted: **NumPy arrays and/or pandas DataFrames**.
- Conversion: `rpy2.robjects` + `numpy2ri`/`pandas2ri`.
- R calls: invoke the actual `RobStatTM::*` functions (not subprocess + JSON).
- Return objects: **Python dataclass (or named dict)** whose fields mirror R return names.
- Global `set_conversion(default_converter)` at import time to survive Jupyter async boundaries.
- R dot-to-Python underscore mapping: `lmrobdet.control` ⇔ `lmrobdet_control` (document both aliases in every relevant docstring).
- **Deferred `importr("RobStatTM")`**: do not start R at `import robstatm_py`; defer until first wrapper call.

---

## 3. Validation policy (proposal §6, §9.1, §11)

- Existing test-task notebook validates `locScaleM` / `mScale` — 14 automated checks pass with **zero numerical difference**. Treat this as the baseline standard.
- Accuracy metric: $\max_i |y_i^{\text{Py}} − y_i^{\text{R}}|$ across **all return fields**, expected exactly **0** for rpy2-bridge wrappers.
- Speed metric: `timeit` over 100 reps; report R-compute time and rpy2 bridge overhead separately.
- Coverage metric: tracked as "$k$ / 15" (core wrapper set) and "$k$ / 18" (full textbook companion set).

---

## 4. Target function table

`Status` columns reflect repository state on **2026-06-10**. Sources:
- **Wrapper status:** existence in `robstattm/python/robstatpy_comparison_rpy2.ipynb` (demonstration only) vs. installable package (none yet).
- **Testing status:** pytest count (none yet) — the notebook checks count as informal validation.
- **Doc status:** NumPy-style docstring present in installable package (none yet).

| # | R function | Package | Book chapter | Priority | Wrapper status | Testing status | Doc status |
|---|------------|---------|--------------|----------|----------------|----------------|------------|
| 1 | `locScaleM` | RobStatTM | 2 (§2.3, 2.7) | Core / Phase 1 | Demo (notebook) | 14 informal checks pass | Notebook prose only |
| 2 | `mScale` | RobStatTM | 2 (§2.5, 2.6) | Core / Phase 1 | Demo (notebook) | informal checks pass | Notebook prose only |
| 3 | `lmrobM` | RobStatTM | 4 (§4.4) | Core / Phase 1–2 | None | None | None |
| 4 | `rob.linear.test` | RobStatTM | 4 (§4.7) | Core / Phase 2 | None | None | None |
| 5 | `lmrobdetMM` | RobStatTM | 5 (§5.3, 5.9) | **Critical / Phase 2** | Demo (notebook) | informal | Notebook |
| 6 | `lmrobdet.control` | RobStatTM | 5 | Core / Phase 1–2 (helper) | None as standalone | None | None |
| 7 | `pyinit` | **pyinit** (external CRAN) | 5 (§5.7) | Core / Phase 2 | None | None | None |
| 8 | `step.lmrobdet` | RobStatTM | 5 (§5.6) | Core / Phase 2 | None | None | None |
| 9 | `lmrobdetDCML` | RobStatTM | 5 (§5.9) | Core / Phase 2 | None | None | None |
| 10 | `pense` | **pense** (external CRAN) | 5 (§5.1) | Stretch / Phase 6 | None | None | None |
| 11 | `covRobMM` | RobStatTM | 6 (§6.5) | **Critical / Phase 3** | Demo (notebook) | informal | Notebook |
| 12 | `covRobRocke` | RobStatTM | 6 (§6.4.2, 6.4.4) | **Critical / Phase 3** | Demo (notebook) | informal | Notebook |
| 13 | `KurtSDNew` | RobStatTM | 6 (§6.9.2) | Core / Phase 3 | None | None | None |
| 14 | `pcaRobS` | RobStatTM | 6 (§6.11.2) | **Critical / Phase 3** | Demo (notebook) | informal | Notebook |
| 15 | `GSE` | **GSE** (external CRAN) | 6 (§6.12.2) | Stretch / Phase 6 | None | None | None |
| 16 | `TSGS` | **GSE** (external CRAN) | 6 (§6.13) | Stretch / Phase 6 | None | None | None |
| 17 | `BYlogreg` | RobStatTM | 7 (§7.2) | Stretch / Phase 6 | None | None | None |
| 18 | `WBYlogreg` | RobStatTM | 7 (§7.2, primary GLM rec.) | Stretch / Phase 6 | None | None | None |
| 19 | `WMLlogreg` | RobStatTM | 7 (§7.2) | Stretch / Phase 6 | None | None | None |

**Core wrapper set (Phases 1–3, "n / 15" coverage metric):** rows 1–9, 11–14 (13 functions) plus `lmrobdet.control` and a distance-distance diagnostic helper = 15.

**Full textbook companion set (n / 18 metric):** rows 1–9, 11–19 minus 15+16 (GSE/TSGS counted once each) — see proposal §9.1.

### 4.1 Extended scope (added 2026-06-10 — full RobStatTM library)

User clarified that the **whole RobStatTM library** is in scope, not only the proposal's §4 selection. See `docs/coverage_gap_analysis.md` for the audit.

Additional NAMESPACE exports added to scope (8 estimators + 3 diagnostics + 9 ψ-infra + 20 datasets + 13 S3 methods):

| # | R name | Module | Priority | Phase |
|---|--------|--------|----------|-------|
| E1 | `covClassic` | covariance | Core | 3 |
| E2 | `covRob` (dispatcher) | covariance | Core | 3 |
| E3 | `Multirobu` (dispatcher) | covariance | Core | 3 |
| E4 | `prcompRob` | pca | Core | 3 |
| E5 | `fastmve` | covariance | Core | 3 |
| E6 | `DCML` (low-level) | regression | Core | 2 |
| E7 | `cov.dcml` | regression | Core | 2 |
| E8 | `MMPY` | regression | Core | 2 |
| E9 | `SMPY` | regression | Core | 2 |
| D1 | `INVTR2` (robust R²) | regression | Core | 2 |
| D2 | `lmrobdetMM.RFPE` | regression | Core | 2 |
| D3 | `refine.sm` | regression | Core | 2 |
| C1 | `lmrobM.control` | regression | Core | 1–2 |
| ψ | `bisquare`, `huber`, `mopt`, `moptv0`, `opt`, `optv0` (family identifiers) | psi | Core | 1 |
| ψ | `rho`, `rhoprime`, `rhoprime2` | psi | Core | 1 |
| S3 | `print.lmrobdetMM`, `summary.lmrobdetMM`, `print.summary.lmrobdetMM` | n/a (dataclass methods) | Core | 2 |
| S3 | `drop1.lmrobdetMM`, `hatvalues.lmrob` | n/a (dataclass methods) | Core | 2 |
| S3 | `print.lsRobTest` | n/a (dataclass methods) | Core | 2 |
| S3 | `print.prcompRob`, `summary.prcompRob`, `print.summary.prcompRob` | n/a (dataclass methods) | Core | 3 |
| S3 | `summary.covRob`, `print.summary.covRob` | n/a (dataclass methods) | Core | 3 |
| S3 | `summary.covClassic`, `print.summary.covClassic` | n/a (dataclass methods) | Core | 3 |
| DS | 20 dataset loaders (`mineral`, `wine`, `bus`, …) | datasets | Core | Bonding |

**New totals:**
- Estimator wrappers: 19 (proposal) + 12 (additions) = **31**
- ψ infrastructure: **9** identifiers/dispatchers
- Dataset loaders: **20**
- S3 methods exposed as dataclass methods: **13**

Per `docs/coverage_gap_analysis.md §4`, this expansion adds ~54 h to the 350 h budget (404 h total) — still inside the 660–770 h availability budget at 30–35 h/week × 22 weeks.

**Status:** plan tracks the expanded scope; mentor sign-off pending (B-008).

---

## 5. Per-phase requirement summary (mapped to proposal §10)

| Phase | Weeks | Functions | Required artifacts |
|-------|-------|-----------|---------------------|
| Bonding | May 1–24 | n/a | `pyproject.toml`, CI matrix, Sphinx skeleton, RTD project, mentor cadence agreement |
| 1 — Univariate | 1–2 | `locScaleM`, `mScale`, `lmrobdet.control` standalone | rpy2 wrappers (mopt/bisquare/huber × eff 0.85/0.90/0.95), pytest field-by-field, Ch. 2 reproduction notebook |
| 2 — Regression | 3–6 | `lmrobdetMM`, `lmrobdetDCML`, `step.lmrobdet`, `pyinit`, `rob.linear.test` | wrappers + diagnostics (robust R², summary table), mineral dataset notebook (Figs 5.1–5.7), ≥90% coverage |
| **Midterm** | end of W6 | — | Midterm report + all of Phases 1–2 |
| 3 — Cov + PCA | 7–10 | `covRobMM`, `covRobRocke`, `KurtSDNew`, `pcaRobS` | wrappers, wine notebook (Fig 6.3), bus notebook (Fig 6.10), distance-distance + scree plot helpers |
| 4 — Benchmarks | 11–12 | (all above) | timing tables, accuracy tables, contaminated-Gaussian generator |
| 5 — Docs/Pkg/Tutorials | 13–16 | (all above) | RTD live, PyPI release, install guide, tutorial notebooks, contributor guide, polished README |
| 6 — Stretch + native + final | 17–22 | `pense`, `GSE`, `TSGS`, `BYlogreg`, `WBYlogreg`, `WMLlogreg`; native-Python comparisons | stretch wrappers, side-by-side benchmarks, final report and archive |

---

## 6. Risks called out by the proposal (§13)

1. `rpy2` build failures on Windows/macOS → conda-forge + Docker fallback, pinned R versions.
2. R/RobStatTM version drift → CI matrix R 4.3/4.4/4.5; `check_setup()` runtime check.
3. Complex rpy2 type conversions for nested R lists → field-by-field validation tests for each wrapper.
4. Scope of 11 core functions too ambitious → phases ordered by dependency; stretch absorbs slip.
5. Mentor availability over summer → 3 mentors for redundancy, weekly written status updates.

These are tracked live in `project_memory/blockers.md`.

---

## 7. What this document does NOT decide

- Repository name on PyPI (`robstatm-py` is the proposed slug; mentor confirmation pending).
- License choice between MIT and Apache 2.0 (proposal §12 says "to be confirmed with mentors").
- Exact dataclass shapes — designed per function in `docs/research/<fn>.md` and consolidated in `docs/architecture.md`.
- Plot-by-plot R-vs-Python rendering strategy — see `docs/plotting_strategy.md`.
