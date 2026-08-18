# Testing playbook - RobStatTM-Py

How to run **every** test layer in this repo, from strict CI gates to
exploratory permutation grids.

## Quick commands

```bash
# 1. Strict CI suite (454 tests, ~75 s) - numerical parity vs R
pytest tests/ -q

# 2. Exploration workflows (173 tests, ~15 s) - datasets + parameter sweeps +
#    synthetic/ingress/edge pipelines (all R-parity at atol=0, rtol=0)
pytest exploration/ -q

# 3. Combinatorial / synthetic / ingress / edge modules, individually
pytest exploration/test_combinatorial_matrix.py -q
pytest exploration/test_synthetic_pipelines.py -q
pytest exploration/test_data_ingress.py -q
pytest exploration/test_edge_cases.py -q

# 4. Everything (tests + exploration) - 627 tests + 13 notebooks
pytest tests/ exploration/ -q          # add RPM_SKIP_NOTEBOOKS=1 to skip notebooks

# 5. With coverage
pytest tests/ exploration/ --cov=robstattm_py --cov-report=term-missing

# 6. Verbose + print output from demos
pytest exploration/ -v -s
```

## What each layer covers

| Layer | Location | Count | Purpose |
|-------|----------|-------|---------|
| **Strict tier** | `tests/` | 454 | Bit-identical vs R (`atol=0, rtol=0`) |
| **Exploration** | `exploration/test_*.py` | 173 | Textbook workflows, under-documented APIs |
| **Combinatorial** | `exploration/test_combinatorial_matrix.py` | ~45 | Dataset × family × estimator grids |
| **Synthetic pipelines** | `exploration/test_synthetic_pipelines.py` | 42 | numpy-RNG data → every wrapper, full-field R parity |
| **Data ingress** | `exploration/test_data_ingress.py` | 7 | CSV / sklearn / cross-package / pandas-wrangle → R parity |
| **Edge cases** | `exploration/test_edge_cases.py` | 19 | Degenerate inputs fail cleanly or match R exactly |
| **Smoke check** | `verify.py --quick` | ad hoc | Manual one-off check of every estimator family (run with `python`) |
| **Examples** | `docs/examples/*.py` | 5 | Runnable documentation |
| **Playground** | `exploration/run_playground.py` | 10 scenarios | Interactive demos |

### Synthetic / ingress / edge modules (2026-06-15)

These three modules **synthesize or import data in Python**, push the *same* frame
to R, and assert bit-identical (`atol=0, rtol=0`) outputs, see
[DATA_PIPELINES.md](DATA_PIPELINES.md) for the full scenario catalog.

- `test_synthetic_pipelines.py` - `numpy.random.default_rng` data (controlled
  outliers, leverage, rank stress, contamination) → univariate, ψ, regression
  (MM/DCML/M, default + custom control + X/y), covariance
  (MM/Rocke/dispatcher/classic/fastmve/kurt), PCA (prcomp/pcaRobS), GLM
  (BY/WBY/WML), `refine_sm`, externals. Full-field parity (coef, scale, fitted,
  residuals, cov, loadings, deviances), stochastic estimators seeded on both sides.
- `test_data_ingress.py` - alternate sources: `pd.read_csv` round-trip,
  `sklearn.datasets` (diabetes/iris/make_classification),
  `datasets.load("robustbase","coleman")`, and pandas wrangling
  (rename/dropna/query/astype/merge), each preprocessed frame matched to R.
- `test_edge_cases.py` - NaN/Inf → clean `ValueError`; constant/single-column &
  p>n covariance/PCA → clean `RobStatTMRError`; rank-deficient regression →
  NaN-coef bit-parity; GLM separation (BYlogreg parity; WBYlogreg rough edge,
  blocker **B-009**); malformed args → `Type`/`ValueError`.

Shared helpers live in `exploration/_synth.py` (data generators + `push_to_r` /
`reval` / `rm_r` R-globalenv plumbing).

## Strict suite breakdown (`tests/`)

| Module | What it verifies |
|--------|------------------|
| `tests/univariate/` | `loc_scale_m`, `m_scale`, all ψ families |
| `tests/regression/` | MM, DCML, M, step, pyinit, linear test, controls, methods |
| `tests/covariance/` | MM, Rocke, dispatcher, classic, fastmve, kurt_sd_new, summaries |
| `tests/pca/` | `pca_rob_s`, `prcomp_rob`, summaries |
| `tests/glm/` | BY, WBY, WML on skin |
| `tests/psi/` | All 6 families × ρ/ψ/ψ′ × 3 efficiencies |
| `tests/datasets/` | All 20 loaders + cross-package `load()` |
| `tests/test_ui_ergonomics.py` | `to_dict`, `to_r`, X/y API, help, pickle |
| `tests/test_compat_r.py` | R-name aliases (`lmrobdetMM`, etc.) |

## Combinatorial matrix (`test_combinatorial_matrix.py`)

Dimensions multiplied:

1. **Regression grid** - 11 (dataset, formula, estimator, family) combos
2. **R parity spot-check** - mineral / stackloss / shock × mopt/bisquare
3. **Formula vs X/y** - all 3 regression estimators on mineral
4. **Covariance grid** - 9 (estimator, dataset) pairs incl. `corr=True`
5. **Method chains** - summary, predict, hatvalues, rfpe, to_dict
6. **GLM grid** - 4 (method, dataset) pairs
7. **Seed reproducibility** - cov, PCA, regression
8. **Stretch** - `pense`, `gse`, `tsgs` (skip if CRAN pkg missing)
9. **Plotting smoke** - residuals PNG

## Manual smoke scripts

Not collected by pytest; run directly when debugging:

```bash
python verify.py --quick              # every estimator family, end-to-end
python verify.py                      # smoke + full pytest suite
python exploration/run_playground.py all
```

## Examples (documentation smoke)

```bash
python docs/examples/lmrobdet_mm.py
python docs/examples/loc_scale_m.py
python docs/examples/cov_rob_mm.py
python docs/examples/prcomp_rob.py
python docs/examples/by_logreg.py
```

## Notebooks (visual / narrative)

| Notebook | Content |
|----------|---------|
| `notebooks/ch5_mineral.ipynb` | Chapter 5 mineral regression figures |
| `notebooks/ui_demo.ipynb` | Full API tour |
| `robstattm/python/robstatpy_comparison_rpy2.ipynb` | Legacy rpy2 comparison |

## Prerequisites

```bash
pip install -e ".[dev]"
python -c "import robstattm_py as rpm; assert rpm.check_setup()"
```

R packages: `RobStatTM`, `robustbase`, `rrcov`, `pyinit` (required);
`pense`, `GSE` (optional, for stretch tests).

## Gaps / not yet automated

- Time-series example scripts (`ar1.R`, …) - no NAMESPACE exports
- Full 26 textbook R script reproductions as notebooks
- Native matplotlib plotting (Path B in architecture doc)
- Multi-platform CI matrix (Linux / macOS / Windows × R versions)

Promote passing exploration cases into `tests/` when they should become CI gates.
