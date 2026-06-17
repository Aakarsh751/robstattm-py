# Coverage Gap Analysis — full RobStatTM library

**Trigger:** the user clarified scope on 2026-06-10: the whole RobStatTM library is in scope, not just the 19 proposal §4 functions.

**Method:** every export in `robstattm/RobStatTM-master/NAMESPACE` + every S3 method + every dataset + every documented `.Rd` page cross-checked against `docs/proposal_requirements.md §4` and `docs/research/`.

---

## 1. Full RobStatTM export inventory (from NAMESPACE)

### 1.1 Functions exported (47)

Grouped by role:

**Estimators — already in plan (19, including aliases):**
`locScaleM` / `MLocDis`, `scaleM` (and `mscale` internal), `lmrobM`, `lmrobM.control`, `lmrobdetMM`, `lmrobdet.control`, `lmrobdetDCML`, `step.lmrobdetMM`, `rob.linear.test` / `lsRobTestMM` / `lmrobdetLinTest`, `covRobMM` / `MMultiSHR`, `covRobRocke` / `RockeMulti`, `KurtSDNew` / `initPP`, `pcaRobS` / `SMPCA`, `BYlogreg` / `logregBY`, `WBYlogreg` / `logregWBY`, `WMLlogreg` / `logregWML`.

**Estimators — NOT in original plan, NOW IN SCOPE (8):**

| R export | Purpose | Phase placement |
|----------|---------|-----------------|
| `covClassic` | **Classical** Pearson covariance returning a `covClassic` object; the side-by-side baseline used in distance–distance plots | Phase 3 (with `covRobMM`) |
| `covRob` | **Generic dispatcher** (`type="MM"|"Rocke"|"auto"`); chooses `covRobMM` for $p<10$ and `covRobRocke` for $p\ge 10$ | Phase 3 — the natural high-level entry point |
| `prcompRob` | **`prcomp`-shaped wrapper** around `pcaRobS`; same return shape as base R `prcomp` | Phase 3 (with `pcaRobS`) |
| `DCML` | Lower-level DCML core called by `lmrobdetDCML` and also exported directly | Phase 2 (small extra) |
| `cov.dcml` | DCML covariance helper used by `lmrobdetDCML`'s standard errors | Phase 2 (small extra) |
| `MMPY` | MM with Peña–Yohai init — exported helper used by `lmrobdetMM` internals; users sometimes call directly | Phase 2 |
| `SMPY` | S+M with Peña–Yohai init — same role | Phase 2 |
| `Multirobu` | Top-level dispatcher in `Multirobu.R` (auto-picks Rocke vs MM by `p`) | Phase 3 — same role as `covRob` |
| `fastmve` | Fast **Minimum Volume Ellipsoid** initial covariance estimator | Phase 3 (small extra; auxiliary) |

**Diagnostics / scoring — NOT in original plan, NOW IN SCOPE (3):**

| R export | Purpose | Phase placement |
|----------|---------|-----------------|
| `INVTR2` | Robust $R^2$ (Invariant TR²); used inside `lmrobdetMM` but exported separately too | Phase 2 (small extra) |
| `lmrobdetMM.RFPE` | RFPE score for an existing `lmrobdetMM` fit (model selection criterion) | Phase 2 (small extra) |
| `refine.sm` | Public hook for the S→M refinement step | Phase 2 (small extra) |

**ψ-function infrastructure — NOT in original plan, NOW IN SCOPE (9):**

| R export | Purpose |
|----------|---------|
| `bisquare` | Bisquare ψ family identifier + tuning constant table |
| `huber` | Huber ψ family |
| `mopt` | Modified-optimal ψ (default for `lmrobdetMM`) |
| `moptv0` | Variant of `mopt` (v0 calibration) |
| `opt` | Yohai optimal ψ |
| `optv0` | Variant of `opt` |
| `rho` | Apply $\rho$ given a family + tuning |
| `rhoprime` | $\psi = \rho'$ |
| `rhoprime2` | $\psi' = \rho''$ |

These are the low-level surface a user needs when implementing custom robust loss diagnostics or extending the package. Wrapped as a small `robstatm_py.psi` submodule.

### 1.2 S3 methods exported (13) — ✅ ALL PORTED (drop1 closed 2026-06-14)

All become **dataclass methods** in Python (or module-level helpers when the operation acts on a fit object). `drop1.lmrobdetMM` was the last remaining gap and is now implemented (`fit.drop1()` / `rpm.drop1_lmrobdet`), strict-tier verified in `tests/regression/test_drop1.py`.

| R S3 method | Python equivalent | Notes |
|-------------|-------------------|-------|
| `print.lmrobdetMM` | `LmrobdetMMResult.__repr__` | Short summary |
| `summary.lmrobdetMM` | `LmrobdetMMResult.summary() -> SummaryTable` | Long summary printed via `print(.summary())` |
| `print.summary.lmrobdetMM` | `SummaryTable.__repr__` | |
| `drop1.lmrobdetMM` | ✅ `fit.drop1(scope=...)` method + `rpm.drop1_lmrobdet(fit, scope=...)` | Single-term-deletion RFPE table; bit-identical to R |
| `hatvalues.lmrob` | `LmrobdetMMResult.hatvalues()` (and `LmrobMResult.hatvalues()`) | Leverage diagnostics |
| `print.lsRobTest` | `RobLinearTestResult.__repr__` | |
| `print.prcompRob` | `PrcompRobResult.__repr__` | |
| `summary.prcompRob` | `PrcompRobResult.summary()` | Prop var table |
| `print.summary.prcompRob` | `SummaryTable.__repr__` | |
| `summary.covRob` | `CovRobResult.summary()` | |
| `print.summary.covRob` | `SummaryTable.__repr__` | |
| `summary.covClassic` | `CovClassicResult.summary()` | |
| `print.summary.covClassic` | `SummaryTable.__repr__` | |

### 1.3 Datasets (20)

All 20 ship with RobStatTM. Every book example uses one. **All must be loadable from Python** — currently planned only as an afterthought (`robstatm_py.datasets.mineral()` etc).

| Dataset | Used by | Chapter |
|---------|---------|---------|
| `alcohol` | textbook example | 2 |
| `algae` | `algae.R` example | 5 |
| `biochem` | `biochem.R` example | 4 |
| `breslow.dat` | textbook example | 7 |
| `bus` | `bus.R` example | 6 |
| `flour` | `flour.R` example | 4 |
| `glass` | textbook example | 6 |
| `hearing` | textbook example | 5 |
| `image` | textbook example | 6 |
| `leuk.dat` | `leukemia.R` example | 7 |
| `mineral` | **flagship example** | 5 |
| `neuralgia` | `neuralgia.R` ? | 7 |
| `oats` | `oats.R` example | 4 |
| `resex` | `resex.R` example | 2/4 |
| `shock` | `shock.R` example | 5 |
| `skin` | `skin.R` example | 7 |
| `stackloss` | textbook example | 4/5 |
| `vehicle` | `vehicle.R` example | 6 |
| `waste` | textbook example | 5 |
| `wine` | **flagship example** | 6 |

Each loaded via `robstatm_py.datasets.<name>() -> pd.DataFrame` with the **same column names as R** and a docstring lifted from the corresponding `.Rd` man page.

### 1.4 Internal but worth exposing as private utilities

These are unexported in NAMESPACE but the user (esp. textbook reproducers) sometimes touches them:

- `lmrob.MM`, `lmrob.S`, `lmrob.fit` (Mächler/Koller MM internals) — accessed via `RobStatTM:::lmrob.MM`. **Not** exposed publicly.
- `splitFrame`, `lmrob.tau`, `lmrob.hatmatrix`, `outlierStats` — internal diagnostics. Not exposed.
- `Mpsi`, `Mchi`, `Mwgt`, `MrhoInf` — Mächler ψ/χ/wgt helpers. **Worth exposing** in `robstatm_py.psi` because user-written diagnostics commonly need them. Phase 2 small extra.

---

## 2. Examples-script coverage

> **Status (2026-06-14): EXECUTED.** The table below is the original *planning*
> view. The **authoritative, verified triage** and conversion plan live in
> **`docs/notebook_plan.md`**. **All 18 group-A+B scripts are now reproduced**
> across the flagship notebooks + six chapter galleries (`notebooks/gallery/`)
> + `external_demo.ipynb`, every one CI-executed by `tests/test_notebooks.py`
> (full suite 442 passing). The 8 group-C scripts (TS +
> `robustvarComp`/`robustarima`/`glmrob`) are out of scope and registered in
> `notebooks/README.md`. The "Phase N" labels below were estimates, not
> completion claims.
>
> Reproduced → notebook map: `flour`→ch2; `shock`,`oats`→ch4;
> `algae`,`ExactFit`,`wood`,`step`→ch5; `biochem`,`vehicle`,`bus`,`wine1`→ch6;
> `leukemia`,`skin`→ch7; `fitmodelsRobStatTM`,`VignetteRobStatTM`→vignette;
> `mineral`→ch5_mineral; `wine`→ch6_wine; pense/gse/tsgs→external_demo.

`robstattm/examples-scripts/` contains 26 scripts. Each must be a reproducible Python notebook for "the whole library" claim to hold:

| Script | Estimator(s) demoed | Notebook status |
|--------|---------------------|-----------------|
| `algae.R` | `lmrobM` / `lmrobdetMM` | Phase 2 notebook |
| `ar1.R` | (TS — out of strict scope) | **Marked out-of-scope** unless mentor expands; logged below |
| `ar3.R` | (TS — out of scope) | same |
| `autism.R` | `lmrobdetMM` / GLM | Phase 6 notebook |
| `biochem.R` | `lmrobM` | Phase 1–2 notebook |
| `bus.R` | `pcaRobS` | Phase 3 notebook (already planned) |
| `epilepsy.R` | GLM logistic | Phase 6 notebook |
| `ExactFit.R` | `lmrobdetMM` edge case | Phase 2 notebook |
| `fitmodelsRobStatTM.R` | aggregator | Phase 5 tutorial |
| `flour.R` | `lmrobM` | Phase 2 |
| `identAR2.R` / `identMA1.R` / `MA1-AO.R` | TS identification | **Out of scope** |
| `leukemia.R` | `logregWBY`/`logregBY` (uses `robust::leuk.dat`) | group B — ch7 gallery |
| `mineral.R` | `lmrobdetMM` Figs 5.1–5.7 | ✅ DONE `ch5_mineral.ipynb` |
| `oats.R` | `lmrobM` | group A — ch4 gallery |
| `resex.R` | `robustarima` (TS) — **out of scope** | group C |
| `shock.R` | `lmrobM` | group A — ch4 gallery |
| `skin.R` | `WBYlogreg`/`BYlogreg`/`WMLlogreg` (+ `robust::glmRob` comparator) | group B — ch7 gallery |
| `step.R` | `step.lmrobdetMM` | Phase 2 |
| `vehicle.R` | `covRobRocke`, `pcaRobS` | Phase 3 |
| `VignetteRobStatTM.R` | end-to-end vignette | Phase 5 |
| `wine.R` | `covRobMM`/`pcaRobS` Fig 6.3 | ✅ DONE `ch6_wine.ipynb` |
| `wine1.R` / `wineDougtest.R` | `covRobMM`/`covRobRocke` | group A — ch6 gallery |
| `wood.R` | `lmrobdetMM` | group A — ch5 gallery |
| `autism.R` | `robustvarComp::varComprob` — **out of scope** | group C |
| `epilepsy.R` | `robustbase::glmrob` — **out of scope** | group C |

**Time-series scripts (`ar1.R`, `ar3.R`, `identAR2.R`, `identMA1.R`, `MA1-AO.R`)**: RobStatTM ships them but the package's TS functions (e.g. AR fitting with robust filters) **are not exported** in `NAMESPACE`. They live in the example scripts only. This is a genuine gray zone for "the whole library":

- If "whole library" means **every exported function in NAMESPACE** → TS scripts are out of scope (no functions to wrap).
- If "whole library" means **everything reproducible** → we need to port the inline R code of these scripts into Python, which means **re-implementing** AR/MA fitting with robust filters.

**Recommendation (logged as B-007):** mentor decision. Default = NAMESPACE-only scope; document the TS scripts as "uses inline R code, see file" in `docs/coverage_gap_analysis.md` so it's transparent.

---

## 3. Updated function table (post-gap)

Total functions to wrap: **19 (original) + 8 (estimators added) + 3 (diagnostics) + 9 (ψ infra) = 39**, plus 13 S3 methods exposed as dataclass methods, plus 20 dataset loaders.

The updated, authoritative function table replaces the table in `docs/proposal_requirements.md §4` with this expanded list. See §5 for the move.

### 3.1 Newly-in-scope research docs needed

`docs/research/` will gain these light-weight reports (one section each — they're small surfaces):

- `covClassic.md`, `covRob.md`, `prcompRob.md`, `Multirobu.md`, `fastmve.md`
- `DCML.md`, `cov.dcml.md`, `MMPY.md`, `SMPY.md`
- `INVTR2.md`, `lmrobdetMM.RFPE.md`, `refine.sm.md`, `lmrobM.control.md`
- `psi_families.md` (covers `bisquare`/`huber`/`mopt`/`moptv0`/`opt`/`optv0`/`rho`/`rhoprime`/`rhoprime2` in one doc — they share a single dispatcher)
- `datasets.md` (covers all 20 with one report — they share one loader pattern)

S3 methods are documented per-dataclass in the respective wrapper research doc (not separate files).

---

## 4. Implementation-plan impact

The added 20 wrappers + 13 S3 methods + 20 dataset loaders is **roughly +30% scope**. Re-budget:

| Phase | Old hours | Added work | New hours |
|-------|-----------|------------|-----------|
| Bonding | 30 | dataset loader skeleton (1 day) | 32 |
| Phase 1 | 30 | `psi_families` (psi module is small + uniform) | 35 |
| Phase 2 | 70 | `DCML`, `cov.dcml`, `MMPY`, `SMPY`, `INVTR2`, `lmrobdetMM.RFPE`, `refine.sm`, `lmrobM.control`, `drop1`, `hatvalues` S3 + summary methods | 90 |
| Phase 3 | 70 | `covClassic`, `covRob`, `Multirobu`, `prcompRob`, `fastmve` + summary methods | 85 |
| Phase 4 | 30 | benchmark coverage of the new estimators | 32 |
| Phase 5 | 60 | docs for ~20 new items + dataset gallery | 70 |
| Phase 6 | 60 | unchanged scope | 60 |
| **Total** | **350** | **+54** | **404** |

The proposal commits 350 hours at 30–35 h/week × 22 weeks = **660–770 h available**. So 404 h is comfortably inside the time budget, but the **proposal scope statement** to the mentors needs updating.

**Action:** raise with mentors at the first Bonding meeting. Two paths:
- (a) Mentors accept the expanded scope (likely — the proposal §4 explicitly says "target function set" implying possible expansion).
- (b) Mentors keep the original 19 plus the dataset/S3/psi auxiliaries (because those are clearly required for usability), and defer `covClassic`/`covRob`/`prcompRob`/etc. to v0.2.0.

Tracked as B-008 in `project_memory/blockers.md`. **Until mentors confirm, the plan tracks the expanded scope but does not lock it.**

---

## 5. What's updated in the rest of the docs

- `docs/proposal_requirements.md §4` will be amended to add a **§4-extended** table covering the additions, leaving the original 19 marked "core" for traceability with the submitted proposal.
- `docs/dependency_map.md §3` will gain rows for `covClassic` (RobStatTM only), `covRob` (depends on whichever sub-estimator runs), `prcompRob` (rrcov), `fastmve` (RobStatTM only), `DCML` (pyinit, robustbase), the ψ family (RobStatTM only).
- `docs/implementation_plan.md` weekly tables will be amended to fold the new items into the matching weeks (no week added; existing weeks gain 1–2 small items each).
- `project_memory/decisions.md` will gain D-011 (scope expansion to full library) and D-012 (S3 methods become dataclass methods).
- `project_memory/blockers.md` will gain B-007 (TS-script scope) and B-008 (mentor sign-off on expanded scope).

---

## 6. What stays out of scope

- The 5 time-series example scripts (`ar1.R`, `ar3.R`, `identAR2.R`, `identMA1.R`, `MA1-AO.R`) until mentors expand.
- Internal helpers under `R/lmrob.MM.R` and `R/psiFuns.R` that are not exported — they remain accessible via `RobStatTM:::` for power users but are not wrapped.
- The C/Fortran kernels in `src/` — these are built by `install.packages("RobStatTM")`; we never touch them.
- Compiled `Mpsi`/`Mchi`/`Mwgt`/`MrhoInf` come from the underlying R/C — we expose them through Python wrappers but do **not** reimplement them in C.
