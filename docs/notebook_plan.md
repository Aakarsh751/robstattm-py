# Notebook & Example-Script Conversion Plan

**Created:** 2026-06-13. **Owner:** implementation track after the stretch externals (D-018).
**Purpose:** close the two gaps surfaced on 2026-06-13 — (a) no CI verifies the
notebooks, and (b) most of the 26 RobStatTM example scripts are not yet
reproduced in Python.

> **STATUS — EXECUTED 2026-06-14.** All four deliverables shipped and green:
> D1 ✅ `tests/test_notebooks.py` (executes all 13 notebooks via nbclient),
> D2 ✅ six chapter galleries under `notebooks/gallery/`,
> D3 ✅ `notebooks/external_demo.ipynb`,
> D4 ✅ `notebooks/README.md` out-of-scope register.
> Full suite now **442 passing** (429 unit + 13 notebooks). All group A+B
> scripts (18) reproduced; group C (8) documented out of scope.

---

## 1. Current state (verified 2026-06-13)

**6 notebooks exist and all execute cleanly end-to-end** (verified via `nbclient`,
6/6 OK):

| Notebook | Demonstrates | Reproduces R script |
|---|---|---|
| `notebooks/ch5_mineral.ipynb` | `lmrobdet_mm`, Figs 5.1–5.7 | `mineral.R` |
| `notebooks/ch6_wine.ipynb` | `cov_rob_mm` / `pca_rob_s`, Fig 6.3 | `wine.R` |
| `notebooks/ui_demo.ipynb` | full UX tour | — |
| `notebooks/tutorials/01_quickstart.ipynb` | 5-minute tour | — |
| `notebooks/tutorials/02_outlier_detection.ipynb` | outlier workflow | — |
| `notebooks/tutorials/03_from_R.ipynb` | R→Python porting guide | — |

**Gaps:**
1. No automated test executes these notebooks — they can silently break.
2. ~2 of 26 example scripts are reproduced; the rest are planned, not built.
3. The new external wrappers (`pense`/`gse`/`tsgs`) have no demo notebook.

---

## 2. Example-script triage (all 26)

Classified by whether the script's estimators are wrapped in `robstatm_py`.
Verified by grepping each script's actual function calls on 2026-06-13.

### A. Convertible — uses only wrapped functions (15)

| Script | Estimator(s) | Target notebook |
|---|---|---|
| `mineral.R` | `lmrobdetMM` | ✅ `ch5_mineral.ipynb` (done) |
| `wine.R` | `covRobMM`, `pcaRobS` | ✅ `ch6_wine.ipynb` (done) |
| `algae.R` | `lmrobdetMM` | Ch5 regression gallery |
| `ExactFit.R` | `lmrobdetMM` (exact-fit edge case) | Ch5 regression gallery |
| `wood.R` | `lmrobdetMM` | Ch5 regression gallery |
| `shock.R` | `lmrobM` | Ch4 regression gallery |
| `oats.R` | `lmrobM` | Ch4 regression gallery |
| `flour.R` | `locScaleM` | Ch2 univariate gallery |
| `step.R` | `lmrobdetMM`, `step.lmrobdetMM` | Ch5 model-selection |
| `bus.R` | `pcaRobS` | Ch6 multivariate gallery |
| `vehicle.R` | `covRobRocke` | Ch6 multivariate gallery |
| `wine1.R` | `covRobMM` | Ch6 (variant of wine) |
| `wineDougtest.R` | `covRobMM`, `covRobRocke` | Ch6 (variant of wine) |
| `fitmodelsRobStatTM.R` | `covRob`, `lmrobdetMM` | end-to-end tutorial |
| `VignetteRobStatTM.R` | `covRob`, `lmrobdetMM` | end-to-end vignette |

### B. Convertible core + external comparator (3)

The robust estimator is ours; the script also calls a non-RobStatTM package
purely as a *classical/comparison* baseline. We reproduce the robust part and
either drop the comparator or substitute a Python equivalent.

| Script | Our estimator | External comparator (handling) |
|---|---|---|
| `skin.R` | `WBYlogreg`/`BYlogreg`/`WMLlogreg` | `robust::glmRob` (drop, or note as out-of-scope) |
| `leukemia.R` | `logregWBY`/`logregBY` | `data(..., package='robust')` (use our `datasets.leuk_dat`) |
| `biochem.R` | (re-grep at build; mostly data/plots) | — |

### C. Out of scope — depend on non-wrapped external packages (8)

These cannot be reproduced without wrapping packages outside the project scope.
Documented as out-of-scope; **not** silently skipped.

| Script | Blocking dependency | Reason |
|---|---|---|
| `autism.R` | `robustvarComp::varComprob` | robust variance-components — not in scope |
| `resex.R` | `robustarima` | robust ARIMA — TS, not in NAMESPACE |
| `ar1.R` | RobStatTM TS (not exported) | B-007 time-series gray zone |
| `ar3.R` | RobStatTM TS (not exported) | B-007 |
| `identAR2.R` | RobStatTM TS (not exported) | B-007 |
| `identMA1.R` | RobStatTM TS (not exported) | B-007 |
| `MA1-AO.R` | RobStatTM TS (not exported) | B-007 |
| `epilepsy.R` | `glmrob` (robustbase GLM) | not a wrapped RobStatTM function |

**Decision rule:** scope = "every estimator exported by RobStatTM (+ pense/GSE/TSGS)".
Scripts whose *core* estimator is one of those are in scope (groups A+B). Scripts
whose core estimator is an unrelated external package (group C) are out of scope
and listed transparently here (ties into B-007 for the TS subset).

---

## 3. Deliverables

### D1 — Notebook CI test (priority 1) ✅ DONE 2026-06-14
`tests/test_notebooks.py`: parametrized over every `notebooks/**/*.ipynb`,
executes each with `nbclient` (already installed), asserts no `CellExecutionError`.
- Marked `@pytest.mark.slow` and `@needs_r` (they need the R bridge).
- Honors the Windows `R_HOME`/PATH bootstrap (each notebook already has a bootstrap cell).
- A `--no-notebooks` opt-out via an env var so the fast unit loop stays fast.
- Acceptance: `pytest tests/test_notebooks.py` → all existing notebooks pass.

### D2 — Chapter reproduction galleries (priority 2) ✅ DONE 2026-06-14
Convert group A+B scripts into **consolidated per-chapter notebooks** (not 1:1 —
that would be 15 near-duplicate files). Proposed structure:
- `notebooks/gallery/ch2_location_scale.ipynb` — `flour`
- `notebooks/gallery/ch4_regression.ipynb` — `oats`, `shock`, `biochem`
- `notebooks/gallery/ch5_regression.ipynb` — `algae`, `ExactFit`, `wood`, `step`
- `notebooks/gallery/ch6_multivariate.ipynb` — `bus`, `vehicle`, `wine1`, `wineDougtest`
- `notebooks/gallery/ch7_glm.ipynb` — `skin`, `leukemia`
- `notebooks/gallery/vignette.ipynb` — `fitmodelsRobStatTM`, `VignetteRobStatTM`

Each cell block: short markdown context → Python reproduction → (where the book
shows a figure) a plot. Every gallery notebook is covered by D1's CI test.

### D3 — External-wrappers demo (priority 2) ✅ DONE 2026-06-14
`notebooks/external_demo.ipynb`: `pense` path + `pense_cv` on a textbook
regression dataset; `gse` on a dataset with injected missingness; `tsgs` on
cell-wise contamination. Covered by D1.

### D4 — Out-of-scope register (priority 3) ✅ DONE 2026-06-14
A short `notebooks/README.md` table listing group C with the blocking dependency,
so a reader never wonders "where's `autism.R`?". Links back to B-007.

---

## 4. Verification policy (new)

Per **D-019** (to be recorded): a notebook is "done" only when it is (a) executed
clean by `tests/test_notebooks.py` in the same run as the unit suite, and (b)
its numeric claims, where it asserts equality to R, use the strict tier. Figures
are visual-only (no pixel assertions) unless a `pytest-mpl` baseline is added.

---

## 5. Sequencing

1. **D1 first** (CI test) — locks in the 6 existing notebooks so D2/D3 can't
   regress them.
2. **D3** (external demo) — small, exercises the freshest code.
3. **D2** (galleries) — the bulk; one chapter notebook at a time, each added to
   D1's sweep as it lands.
4. **D4** (register) — trivial, last.

Out-of-scope group C stays out until B-007 (TS) and any mentor decision on
`robustvarComp`/`robustarima` is resolved.

---

## 5a. Execution notes & deviations from the plan (2026-06-14)

- **`biochem.R` placed in ch6, not ch4.** It is Example 6.1 (multivariate) and
  uses only classical mean/var/correlation — it is the classical baseline that
  motivates the robust estimators, so it opens the ch6 gallery.
- **`wine1.R` split.** Its `covRobMM` (independent-contamination) part is in
  `gallery/ch6_multivariate.ipynb`; its `GSE::GSE` / `GSE::TSGS`
  (missing-data / cell-wise) parts are reproduced in `external_demo.ipynb`,
  which is the natural home for the external wrappers.
- **`oats.R` robust ANOVA via MM fits.** `oats.R` calls `rob.linear.test` on
  `lmrobM` fits, but `rpm.rob_linear_test` wraps `rob.linear.test` for
  `lmrobdetMM` fits (its documented contract), so the ch4 gallery shows the
  robust nested-model test on MM fits of the oats data (and the `lmrobM`
  coefficients/scale separately).
- **Stochastic estimators are seeded for parity.** `lmrobM` / `lmrobdetMM` /
  `covRobRocke` / `pcaRobS` / `covRobMM` use random subsampling, so every
  in-notebook bit-equality cross-check seeds Python and R identically
  (`set_seed(N)` then `set.seed(NL)`) before fitting each side.
- **`wineDougtest.R` not present.** The plan's §2 table mentioned it, but it is
  not in `robstattm/examples-scripts/`; `wine1.R` covers the same covRobMM/Rocke
  territory.

## 6. What this does NOT include
- Wrapping `robustvarComp`, `robustarima`, or `robustbase::glmrob` (out of scope).
- Pixel-level figure regression (deferred; `docs/plotting_strategy.md` covers the
  eventual `pytest-mpl` path).
- Time-series reproductions (B-007).
