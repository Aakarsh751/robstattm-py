# Implementation Plan

Maps proposal §10 onto concrete week-by-week tasks, files touched, tests written, and exit criteria. The plan deliberately fits inside 22 weeks × 30–35 h/week ≈ 350 h. All deliverables are tracked in `project_memory/progress_log.md`.

---

## 1. Calendar overview

| Phase | Weeks | Dates (2026) | Hours | Exit gate |
|-------|-------|--------------|-------|-----------|
| Community Bonding | — | May 1 – May 24 | 30 | Package scaffold + CI green + Sphinx skeleton + mentor sign-off |
| Phase 1 — Univariate | 1–2 | May 25 – Jun 7 | 30 | `locScaleM` + `mScale` pytest green vs R; Ch 2 notebook |
| Phase 2 — Regression | 3–6 | Jun 8 – Jul 5 | 70 | All regression wrappers pytest green; mineral notebook; ≥ 90% coverage on `regression/` |
| **Midterm** | end of 6 | Jul 6 – Jul 10 | — | Mentor evaluation report |
| Phase 3 — Cov + PCA | 7–10 | Jul 13 – Aug 9 | 70 | Cov + PCA wrappers green; wine + bus notebooks |
| Phase 4 — Benchmarks | 11–12 | Aug 10 – Aug 23 | 30 | Benchmark notebook (timing + accuracy tables) merged |
| Phase 5 — Docs / Pkg / Tutorials | 13–16 | Aug 24 – Sep 20 | 60 | RTD live, PyPI 0.1.0 published, install guide complete |
| Phase 6 — Stretch + native + final | 17–22 | Sep 21 – Nov 2 | 60 | Stretch wrappers (pense/GSE/TSGS/GLM where time permits), native comparisons, final report |

---

## 2. Community Bonding (May 1 – May 24)

| Deliverable | File(s) | Definition of done |
|-------------|---------|---------------------|
| `pyproject.toml` with PEP 621 metadata, deps from `docs/dependency_map.md §4` | `/pyproject.toml` | `pip install -e .` succeeds in a clean venv |
| Package scaffold | `src/robstatm_py/__init__.py`, `_r.py`, `_converters.py`, `_errors.py`, `utils/check_setup.py`, `py.typed` | `import robstatm_py; robstatm_py.check_setup()` runs without starting R |
| `pytest` config | `pyproject.toml [tool.pytest.ini_options]` + `tests/conftest.py` | `pytest -q` collects 0 tests, exits 0 |
| GitHub Actions CI | `.github/workflows/test.yml`, `.github/workflows/docs.yml` | lint + build matrix green |
| Sphinx + RTD skeleton | `docs_sphinx/` (separate from this planning `docs/`), `.readthedocs.yaml` | RTD project builds the empty skeleton |
| Mentor sign-off | meeting notes in `project_memory/decisions.md` | recorded |

---

## 3. Phase 1 — Univariate (Weeks 1–2, May 25 – Jun 7)

### Week 1 — `locScaleM`, `mScale`

| Day | Task | Files |
|-----|------|-------|
| Mon | Port `MLocDis.R` understanding into `docs/research/locScaleM.md` (already exists from Phase 2 of this planning); implement `univariate/loc_scale_m.py` | `src/robstatm_py/univariate/loc_scale_m.py` |
| Tue | Implement `univariate/m_scale.py` | same dir |
| Wed | Write `tests/univariate/test_loc_scale_m.py` and `test_m_scale.py` (cases 1–4, 7–10 from `docs/validation_strategy.md §3`) | tests/ |
| Thu | Run sweep over `family ∈ {bisquare, huber, mopt}` × `eff ∈ {0.85, 0.90, 0.95}`; all strict-tier vs R | parametrize via pytest |
| Fri | Write NumPy-style docstrings; first Sphinx autodoc render | src/ + docs_sphinx/ |

**Week 1 exit:** 9 family×efficiency × 2 wrappers × ≥ 4 test cases = ≥ 72 strict-tier assertions green.

### Week 2 — `lmrobdet.control` (standalone) + Ch 2 notebook

| Day | Task | Files |
|-----|------|-------|
| Mon | Implement `regression/control.py::lmrobdet_control` | src/ |
| Tue | Test against `R("lmrobdet.control(...)")` for all keyword combinations from `lmrobdet.control.Rd` | tests/regression/test_control.py |
| Wed–Thu | Build Chapter 2 reproduction notebook (`notebooks/ch2_loc_scale.ipynb`) using the new wrappers | notebooks/ |
| Fri | Integration test that runs the notebook end-to-end (`nbmake`) and asserts no exceptions | tests/integration/ |

---

## 4. Phase 2 — Regression (Weeks 3–6, Jun 8 – Jul 5)

| Week | Functions | Notebook | Exit |
|------|-----------|----------|------|
| 3 | `lmrobdetMM` (formula, coef, residuals, rweights, scale) | — | pytest green for cases 1–11 from §3 of validation strategy |
| 4 | `lmrobdetMM` diagnostics (`r_squared`, `summary()`), `lmrobdetDCML` | — | summary table mirrors R `summary()` exactly |
| 5 | `step.lmrobdet`, `pyinit`, `rob.linear.test`; mineral dataset notebook | `notebooks/ch5_mineral.ipynb` | Figures 5.1–5.7 reproduced (Path A for the published ones) |
| 6 | Coverage hardening; **midterm report** | `MIDTERM.md` | `pytest --cov=robstatm_py.regression --cov-fail-under=90` green |

### Critical path notes
- `lmrobdetMM` depends on `pyinit` for typical defaults — order matters: implement `pyinit` wrapper **with** `lmrobdetMM` in Week 3, not after, so we can use `initial="pyinit"` paths in tests.
- `lmrobdetDCML` depends hard on `pyinit` (`DCML.R:165`); blocked if pyinit isn't working on the test runner OS.

---

## 5. Phase 3 — Covariance + PCA (Weeks 7–10, Jul 13 – Aug 9)

| Week | Functions / artifacts | Notebook |
|------|------------------------|----------|
| 7 | `covRobMM` (center, cov, cor, MD, weights) | — |
| 8 | `covRobRocke`, `KurtSDNew`; wine notebook (Fig 6.3) | `notebooks/ch6_wine.ipynb` |
| 9 | `pcaRobS` (eigenvectors, prop var, scores); bus notebook (Fig 6.10) | `notebooks/ch6_bus.ipynb` |
| 10 | Distance–distance + scree helpers under `plotting/`; module-wide docs pass; end-to-end integration tests | tests/integration/ |

**Phase-3 exit:** 4 multivariate wrappers green + 2 reproduction notebooks + plotting helpers + ≥ 90% module coverage.

---

## 6. Phase 4 — Benchmarks (Weeks 11–12, Aug 10 – Aug 23)

| Week | Task |
|------|------|
| 11 | `benchmarks/synthetic.py` (contaminated Gaussian generator over `n ∈ {100, 1000, 10000}`, `p ∈ {5, 20, 50}`); `benchmarks/timing.py` (`timeit` over 100 reps) producing a CSV; plotting from CSV to comparison notebook |
| 12 | Accuracy benchmarks: `max | py − R |` across all wrappers and grid points; comparative notebook `notebooks/benchmarks.ipynb` published as PDF in `docs_sphinx/_static/` |

The benchmark CSVs are committed under `benchmarks/results/` with the R/python/rpy2/RobStatTM versions in the filename for traceability.

---

## 7. Phase 5 — Docs / Pkg / Tutorials (Weeks 13–16, Aug 24 – Sep 20)

| Week | Task | Artifact |
|------|------|----------|
| 13 | Complete Sphinx pages for every wrapper; autodoc + custom examples gallery | `docs_sphinx/api/`, `docs_sphinx/examples/` |
| 14 | First PyPI release `0.1.0`: build wheel + sdist, twine upload, write install guide | `INSTALL.md`, GitHub release tag |
| 15 | Three tutorial notebooks (Ch 2, Ch 5 regression, Ch 6 multivariate) — polished, narrated, runnable on Binder | `notebooks/tutorials/` |
| 16 | Final integration tests; `CONTRIBUTING.md`; README polish | repo root |

---

## 8. Phase 6 — Stretch + native + final (Weeks 17–22, Sep 21 – Nov 2)

| Week | Task |
|------|------|
| 17 | `pense` wrapper + tests; `GSE` wrapper + tests |
| 18 | `TSGS` wrapper + tests; `BYlogreg`, `WBYlogreg`, `WMLlogreg` if time permits |
| 19 | Native Python prototype (lowest-effort first: `mScale`); benchmark vs rpy2 wrapper |
| 20 | Second native prototype (`locScaleM`); document methodology and scope limits |
| 21 | Final documentation review; address all outstanding mentor feedback |
| 22 | Final submission: code review, evaluation report, archive of notebooks + benchmarks; PyPI `0.2.0` release if stretch warrants |

---

## 9. Critical-path analysis

```
[Bonding] ─► [Phase 1] ─► [Phase 2 wk3 lmrobdetMM] ─┐
                                                    ├─► [Phase 4 benchmarks]
[Phase 2 wk5 pyinit] ─► [Phase 2 wk5 DCML, step] ───┤
                                                    │
[Phase 3 wk7 covRobMM] ─► [Phase 3 wk9 pcaRobS] ────┘
                                                    │
                                                    ▼
                                          [Phase 5 docs / PyPI]
                                                    │
                                                    ▼
                                          [Phase 6 stretch / native / final]
```

### Highest-risk wrappers
1. **`pyinit`** — external CRAN package, Windows install historically fragile. **Mitigation:** implement and CI-validate on Linux first; explicit skip + clear message on Windows if binary missing.
2. **`lmrobdetDCML`** — depends on `pyinit` *and* on `lmrobdetMM` working correctly. Blocked-until both above are green.
3. **`pcaRobS`** — depends on `rrcov::PcaLocantore`; an `rrcov` API change here would block all Phase-3 reproduction work. **Mitigation:** lock `rrcov` version in `renv.lock`.
4. **`pense`** — large compile, optional. Treat as fully optional; do not block 0.1.0 release on it.

### Prerequisite chain
- Every wrapper depends on the converter layer (`_converters.py`) — implemented in Bonding.
- `lmrobdet_control` is a hard prerequisite for `lmrobdetMM`, `step.lmrobdet`, `lmrobdetDCML`, `rob.linear.test`.
- Distance–distance and scree plot helpers depend on `covRobMM` / `pcaRobS` returning the right fields; finalize dataclass fields in Week 7 / Week 9.

### Slip absorbers
- Phase 6 native-Python work is fully optional and absorbs any slip from Phases 1–5.
- Stretch GLM wrappers can drop out without affecting the proposal's "core 15" deliverable.

---

## 10. Deliverable summary at end of GSoC

- `pip install robstatm-py == 0.1.0` (or 0.2.0 if stretch lands).
- 15 (core) — 18 (full set) wrappers, each with strict-tier R parity tests.
- ≥ 90% coverage on every module.
- Sphinx docs live on RTD.
- 4 notebooks (Ch 2, Ch 5, Ch 6, benchmarks) plus 3 tutorial notebooks.
- Benchmark CSVs + accuracy tables.
- Install guide covering Linux / macOS / Windows.
- CI green on the full matrix.
- Final report archived under `docs/final_report.md`.
