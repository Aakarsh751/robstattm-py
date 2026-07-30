# Project Understanding — RobStatTM-Py (GSoC 2026)

**Author of audit:** Claude (planning session)
**Audit date:** 2026-06-10
**Repository root:** `C:\ProfDM_Rproject`
**Branch:** `main`
**Goal restated:** Port the RobStatTM ecosystem to Python through **rpy2 wrappers** that expose RobStatTM functionality to Python users while **guaranteeing numerical equivalence** with the original R implementation. This is **not** a pure-Python re-implementation.

---

## 1. Repository Layout (top level)

```
C:\ProfDM_Rproject\
├── .claude/                              # Claude Code per-project settings
├── .git/                                 # Git metadata
├── .gitignore
├── README.md                             # Top-level README mapping repo to proposal
├── Aakarsh_Resume.pdf                    # Applicant CV (proposal supplement)
├── Robust Statistic via Python GSOC 2026.docx   # Early proposal draft
├── RobStatTM-Py GSOC2026 Proposal.pdf    # Submitted proposal (canonical)
├── get_r_values.R                        # Standalone helper: dumps R reference values
│
├── Accepted_Proposals/                   # Historical accepted GSoC proposals (reference only)
├── Book_Website/                         # Quarto site for the PCRA book (legacy, large)
├── RPCRAwebsite/                         # Newer Quarto book site (subset of Book_Website)
├── Research_2/                           # Background PDFs (cross-sectional factor models, JAM FF92)
├── GSOC/                                 # Acceptance docx
│
├── docs/                                 # Project documentation root (NEW WORK GOES HERE)
│   ├── README.md
│   ├── gsoc2026_proposal/                # LaTeX sources + PDFs of all proposal versions
│   └── misc/                             # robstattm1.Rmd
│
├── pcra/                                 # PCRA Chapter-2 reproducibility comparison
│   ├── docs/                             # PCRA CRAN manual, equivalent plan, comparison PDFs
│   ├── output/                           # Generated comparison PDFs (R vs Python Ch 2)
│   ├── python/                           # ch2_foundations_demo.py + data
│   ├── r/                                # R chapter-2 demo and dep installer
│   └── tools/                            # PDF generators
│
└── robstattm/                            # Core RobStatTM working area
    ├── docs/                             # RobStatTM book PDF, examples guide, conversion guide
    ├── examples-scripts/                 # 26 textbook example R scripts
    ├── python/                           # Existing rpy2 + figures (proposal "test task" artifacts)
    │   ├── figures/                      # Side-by-side R/Python plot PNGs
    │   ├── NOTEBOOKS.md
    │   ├── requirements.txt
    │   ├── robstatpy_comparison.ipynb         # Subprocess + jsonlite path (alternate)
    │   └── robstatpy_comparison_rpy2.ipynb    # Primary rpy2 demonstration notebook
    ├── r/                                # Helper R scripts (data export, example runners)
    ├── README.md
    └── RobStatTM-master/                 # Vendored upstream RobStatTM 1.0.12 source
        ├── DESCRIPTION  NAMESPACE  NEWS.md  README.md
        ├── R/           # 40 .R source files (all estimator implementations)
        ├── man/         # 59 .Rd man pages
        ├── data/        # 20 .RData example datasets
        ├── src/         # C and Fortran kernels (lmrob.c, fastmve.c, rllarsbi.f, erfz.c)
        ├── inst/scripts/
        ├── sandbox/
        └── vignettes/
```

---

## 2. File-by-file inventory

### 2.1 `robstattm/RobStatTM-master/R/` — upstream estimator source (40 files)

Files in this directory are the **canonical R implementations** that the rpy2 wrappers must reproduce exactly. They are read-only reference; we do not edit them.

| File | Purpose | Wraps into target function(s) |
|------|---------|-------------------------------|
| `MLocDis.R` | Joint location/scale M-estimator | `locScaleM` |
| `Multirobu.R` | M-scale, helpers | `mScale` |
| `lmrobdet.R` | MM regression entry points, control object | `lmrobdetMM`, `lmrobdet.control`, `step.lmrobdet`, `lmrobdetMM.RFPE` |
| `lmrob.MM.R` | Internal MM IRLS fit | helper for `lmrobdetMM` |
| `lmrob.lar.R` | LAR initial fit (Koller) | internal |
| `DCML.R` | Distance-constrained MLE | `lmrobdetDCML`, `cov.dcml` |
| `RFPE.R` | Robust final prediction error | model selection |
| `INVTR2.R` | Robust $R^2$ | reporting |
| `lsRobTestMM.R` | Robust linear hypothesis test | `rob.linear.test` |
| `Multirobu.R`, `fastmve.R` | Multivariate robust covariance | `covRobMM`, `covRobRocke` |
| `KurtSDNew.R` | Peña–Prieto kurtosis-driven init | `KurtSDNew` |
| `RobPCA_SM.R`, `prcompRob.R` | Robust PCA via M-scale, S-PCA | `pcaRobS` (SM-PCA) |
| `BYlogreg.R`, `WBYlogreg.R`, `WMLlogreg.R` | Robust logistic regression | three GLM wrappers |
| `psiFuns.R`, `psiFunUtils.R` | Bisquare / Huber / m-opt psi/rho families | infrastructure |
| `utils.R`, `print.lsRobTest.R` | Misc helpers, print methods | n/a |
| `alcohol.R … wine.R` (dataset wrappers) | Dataset documentation stubs | wrapped via `data()` |

### 2.2 `robstattm/RobStatTM-master/src/` — compiled kernels

- `lmrob.c` — fast S-/MM-estimator kernel (originally Koller/Mächler)
- `fastmve.c` — fast minimum volume ellipsoid
- `rllarsbi.f` — Fortran LARS for initial fits
- `erfz.c` + `erfi.c` — error function helpers
- `Makevars`, `init.c`, `RobStatTM.h`

Status: untouched. We rely on these being built in the R installation of RobStatTM ≥ 1.0.12.

### 2.3 `robstattm/python/` — existing rpy2 work

| File | Status | Notes |
|------|--------|-------|
| `robstatpy_comparison_rpy2.ipynb` | **Working — proposal test task** | Demonstrates Part I: `locScaleM`, `mScale`, `lmrobdetMM`, `covRobMM`/`covRobRocke`, `pcaRobS` via `importr("RobStatTM")` + `R('…')` strings. Uses `set_conversion(default_converter)` and helpers `R()`, `rx()`, `r2py()`. 14 automated checks pass. |
| `robstatpy_comparison.ipynb` | Working (alternate) | Subprocess + `jsonlite` JSON round-trip. Kept for benchmark comparison; **not** the primary path. |
| `requirements.txt` | Working | numpy, pandas, matplotlib, scipy, statsmodels, nbformat, nbconvert, rpy2≥3.6.6 |
| `NOTEBOOKS.md` | Working | Describes the two notebooks |
| `figures/` (11 PNGs) | Reference outputs | Pairs of R vs Python plots used as visual regression baselines |

**No installable Python package exists yet** — no `pyproject.toml`, no `pytest` suite, no `src/robstattm_py/`. The GSoC project builds this.

### 2.4 `robstattm/examples-scripts/` — textbook example scripts (26 .R files)

Each script reproduces one example/figure from Maronna et al. (2019). These define the **golden outputs** the wrappers must reproduce.

Most relevant for early phases: `mineral.R`, `wine.R`, `bus.R`, `oats.R`, `flour.R`, `vehicle.R`, `ExactFit.R`, `fitmodelsRobStatTM.R`, `VignetteRobStatTM.R`.

Time series scripts (`ar1.R`, `ar3.R`, `MA1-AO.R`, `identAR2.R`, `identMA1.R`) reference RobStatTM time-series functionality that is **out of proposal scope**.

### 2.5 `robstattm/docs/`

- `RobStatTM Book.pdf` — Maronna et al. (2019) reference
- `RobStatTM Examples Scripts and Data Sets Guide.pdf` — companion to `examples-scripts/`
- `WITH R Robust statistics_ theory and methods.pdf` — textbook PDF
- `RobStatTM_R_to_Python_Conversion_Guide.md` — early hand notes (informal)
- `RobStatTM_Study_and_Setup_Guide.md` — environment notes (informal)

The two `.md` guides are early, informal notes; superseded by `docs/project_understanding.md` (this file) and the rest of the new `docs/` tree.

### 2.6 `pcra/` — PCRA Chapter 2 reproducibility (out-of-band)

This subtree is from the parallel **PCRA** Python equivalent effort, not the RobStatTM-Py deliverable. It contains a Chapter-2 R-vs-Python comparison demo. **Reference only** — does not block the GSoC scope. Keep in place; do not archive (still actively referenced by the top-level README and a mentor request).

### 2.7 `docs/gsoc2026_proposal/`

LaTeX sources, intermediate aux/log/out files, and PDFs for proposal v1 → v4 plus the final `RobStatTM-Py GSOC2026 Proposal.{tex,pdf}`. The submitted document is the v4 / final tex.

Cleanup recommendation: leave LaTeX sources and the **final** PDF; the v1–v3 PDFs are historical. We will not delete them — see §4 below.

### 2.8 `Book_Website/`, `RPCRAwebsite/`

Quarto book sites for the PCRA book. Large; not part of RobStatTM-Py. The top-level git status shows a large staged deletion under `Book_Website/` (auto-generated cache PNGs / appendix LyX/PDF copies that were accidentally tracked). **Reference only** — keep checked-in pieces, do not touch the staged deletions during this planning phase.

### 2.9 `Accepted_Proposals/`, `Research_2/`, `GSOC/`, `Aakarsh_Resume.pdf`

Background / reference. Not on the implementation path.

### 2.10 Configuration & CI

| File | Present? | Notes |
|------|----------|-------|
| `pyproject.toml` | ❌ | To be created in Community Bonding (May 1–24) |
| `setup.cfg` / `setup.py` | ❌ | Not planned (PEP 621 via pyproject.toml only) |
| `pytest.ini` / `tox.ini` | ❌ | To be created |
| `.github/workflows/` | ❌ | CI matrix (Linux/macOS/Windows × R 4.3/4.4/4.5) is a proposal deliverable |
| `requirements.txt` | ✅ (under `robstattm/python/`) | Will be superseded by `pyproject.toml` |
| `.gitignore` | ✅ | Current; needs additions for `__pycache__`, `.pytest_cache`, `.venv` |
| `.readthedocs.yaml` | ❌ | Documentation deliverable (Phase 5, Week 13) |

---

## 3. Current implementation status (against proposal §10 plan)

| Phase | Status |
|-------|--------|
| Community Bonding scaffold (`pyproject.toml`, CI, Sphinx) | **Not started** |
| Phase 1: `locScaleM`, `mScale` wrappers + tests | **Demonstrated in notebook only** (no pytest, no installable package) |
| Phase 2: regression (`lmrobdetMM` etc.) | **Demonstrated in notebook only** |
| Phase 3: covariance + PCA | **Demonstrated in notebook only** |
| Phase 4: benchmarks | **Not started** |
| Phase 5: docs/packaging/tutorials | **Not started** |
| Phase 6: stretch (pense/GSE/TSGS/GLM) + native Python | **Not started** |

**The repo at proposal-submission time contains demonstrations, not the deliverable package.** The deliverable is built during the GSoC coding window starting late May 2026.

---

## 4. Cleanup decisions

The user asked: "organise the folder, do cleanup (dont delete, put them in an archive if useless or not required)".

**Policy adopted:**
- **No file is deleted.** Anything moved goes under `archive/` at the repo root.
- We do **not** touch files that the top-level `README.md` actively references (they are part of the proposal evidence trail).
- We do **not** touch the staged `Book_Website/` deletions already in `git status` — those are pre-existing user-staged changes; resolving them is the user's decision, not this planning agent's.
- We do **not** archive the `pcra/` tree, the `RobStatTM-master/` vendor copy, or any LaTeX source.

**Proposed `archive/` contents (executed in a separate cleanup pass once the user approves):**

| Move from | To | Why |
|-----------|----|-----|
| `Robust Statistic via Python GSOC 2026.docx` | `archive/early_drafts/` | Superseded by the LaTeX proposal v4 |
| `docs/gsoc2026_proposal/proposal.{tex,pdf,aux,log,out}` (v1) | `archive/proposal_history/v1/` | Superseded |
| `docs/gsoc2026_proposal/proposal_v2.*` | `archive/proposal_history/v2/` | Superseded |
| `docs/gsoc2026_proposal/proposal_v4.{aux,log,out}` (no .tex/.pdf — they're the canonical file under a renamed name) | `archive/proposal_history/v4_intermediate/` | Stale aux/log/out |
| `docs/gsoc2026_proposal/proposal_v3 dougComments.pdf` | `archive/proposal_history/v3_comments/` | Comments incorporated |
| `docs/gsoc2026_proposal/related_work_shelved.*` | `archive/proposal_history/shelved/` | Tex file explicitly named "shelved" |
| `Accepted_Proposals/` | `archive/reference_proposals/` | Reference-only historical proposals |
| `Research_2/` | `archive/background_reading/` | Background PDFs, not on implementation path |
| `robstattm/docs/RobStatTM_R_to_Python_Conversion_Guide.md` | `archive/early_notes/` | Superseded by the new `docs/` tree |
| `robstattm/docs/RobStatTM_Study_and_Setup_Guide.md` | `archive/early_notes/` | Superseded |
| `robstattm/RobStatTM-master/sandbox/` | `archive/upstream_sandbox/` | Upstream sandbox; not needed for wrappers |

**Files explicitly NOT archived (kept in place):**
- `RobStatTM-Py GSOC2026 Proposal.pdf` (top-level submitted PDF)
- `docs/gsoc2026_proposal/RobStatTM-Py GSOC2026 Proposal.{tex,pdf}` (canonical source)
- `docs/gsoc2026_proposal/robstatpy_tests.{tex,pdf}` (referenced from the proposal §6)
- `docs/gsoc2026_proposal/pcra_future_work.{tex,pdf}` (live mentor-facing doc)
- `robstattm/RobStatTM-master/{R,man,data,src,inst,vignettes,DESCRIPTION,NAMESPACE,NEWS.md,README.md}` (vendored upstream)
- All of `robstattm/examples-scripts/`, `robstattm/python/`, `robstattm/r/`
- All of `pcra/`
- `Aakarsh_Resume.pdf` (proposal supplement)
- `Book_Website/`, `RPCRAwebsite/` (live websites)
- `get_r_values.R` (used by validation notebooks)

The actual `git mv` operations are deferred to a follow-up pass after the user reviews this plan — see `project_memory/decisions.md` decision D-002.

---

## 5. Relationship to proposal goals

Every file above is tagged in §2 with which proposal deliverable it supports. Key mapping:

| Proposal §4 target function | R source (`RobStatTM-master/R/`) | Status |
|---|---|---|
| `locScaleM` | `MLocDis.R` | ✅ R available; wrapper demo exists |
| `mScale` | `Multirobu.R` | ✅ R available; wrapper demo exists |
| `lmrobM` | `lmrobdet.R` | ✅ R available; wrapper not started |
| `rob.linear.test` | `lsRobTestMM.R` | ✅ R; not started |
| `lmrobdetMM` | `lmrobdet.R`, `lmrob.MM.R` | ✅ R; wrapper demo exists |
| `pyinit` | external R package `pyinit` | ⚠ external dep; **not vendored** |
| `step.lmrobdet` | `lmrobdet.R` | ✅ R; not started |
| `lmrobdetDCML` | `DCML.R` | ✅ R; not started |
| `pense` | external R package `pense` | ⚠ external; **not vendored**; stretch |
| `covRobMM` | `Multirobu.R` | ✅ R; demo exists |
| `covRobRocke` | `Multirobu.R` | ✅ R; demo exists |
| `KurtSDNew` | `KurtSDNew.R` | ✅ R; not started |
| `pcaRobS` | `RobPCA_SM.R`, `prcompRob.R` | ✅ R; demo exists |
| `GSE`, `TSGS` | external R package `GSE` | ⚠ external; stretch |
| `BYlogreg`, `WBYlogreg`, `WMLlogreg` | `BYlogreg.R`, `WBYlogreg.R`, `WMLlogreg.R` | ✅ R; stretch |

---

## 6. Open questions surfaced during the audit

1. **External-R-package vendoring policy.** `pyinit`, `pense`, `GSE` are CRAN packages. Do we vendor them (like `RobStatTM-master/`) or rely on user-side `install.packages()` at first use? Recommendation: rely on `install.packages()` + a `check_setup()` utility (matches proposal §12). See `project_memory/decisions.md` D-003.
2. **Notebook → package migration.** The two `robstattm/python/*.ipynb` notebooks contain ad-hoc wrapper code. We will extract the patterns but not import them; the installable package gets fresh, documented code per the standards in `docs/documentation_standards.md`.
3. **Windows build of `pyinit`.** `pyinit` has historically been hard to install on Windows. Tracked as a risk in `project_memory/blockers.md`.
4. **`rpy2` ≥ 3.6 conversion context.** The proposal calls out that conversion context is lost across Jupyter async boundaries. Confirmed in `robstatpy_comparison_rpy2.ipynb`. Mitigation: call `set_conversion(default_converter)` once at package import. Recorded in `project_memory/decisions.md` D-004.

---

## 7. Next-document pointers

- Proposal-level requirements distilled: → `docs/proposal_requirements.md`
- Per-function research: → `docs/research/<function>.md`
- Dependency graph: → `docs/dependency_map.md`
- Architecture: → `docs/architecture.md`
- Validation policy: → `docs/validation_strategy.md`
- Plotting: → `docs/plotting_strategy.md`
- Implementation timeline + critical path: → `docs/implementation_plan.md`
- Documentation standards: → `docs/documentation_standards.md`
- Implementation rules + quality gates: → `docs/implementation_rules.md`, `docs/quality_gates.md`
- Live memory: → `project_memory/{decisions,progress_log,discoveries,blockers,lessons_learned,resume_prompts}.md`
