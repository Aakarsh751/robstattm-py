# RobStatTM-Py — Exploration & Parameter Playground

This folder is **separate from the main `tests/` suite**. It holds exploratory
workflows that go beyond the five hand-authored examples in `docs/examples/`:
different control settings, less-used datasets, wrappers not yet demoed in
notebooks, and R-vs-Python parity checks under parameter sweeps.

## What is (and is not) reproduced from R?

See **[PARITY.md](PARITY.md)** for the full gap table. Short version:

| Area | Status |
|------|--------|
| **Core estimators** (42/46 NAMESPACE exports) | Wrapped; strict-tier tests in `tests/` |
| **S3 methods** (`summary`, `predict`, `hatvalues`, …) | Ported as dataclass methods |
| **20 datasets** | Loadable as pandas DataFrames |
| **ψ-family helpers** | Full coverage in `robstatm_py.psi` |
| **R `lm()` extras** (`subset`, `weights`, `na.action`) | **Not exposed** on regression wrappers |
| **Some R return fields** (`MD`, `weights`, `qr`, …) | **Not extracted**; available via `fit._r_fit` / `fit.to_r()` |
| **Internal helpers** (`DCML`, `MMPY`, `SMPY`, `cov.dcml`) | **Intentionally not public** |
| **Time-series example scripts** | Out of scope (no NAMESPACE exports) |

Numerical outputs for **exposed parameters** match R bit-for-bit when tested;
this folder extends that verification to combinations the main suite does not sweep.

## Prerequisites

```bash
pip install -e ".[dev]"    # from repo root
# R with RobStatTM, robustbase, rrcov, pyinit installed
python -c "import robstatm_py as rpm; rpm.check_setup()"
```

## Running

```bash
# All exploration tests (skips automatically if R unavailable)
pytest exploration/ -v

# Combinatorial cross-product matrix only
pytest exploration/test_combinatorial_matrix.py -v

# Full package: strict CI + exploration
pytest tests/ exploration/ -q
```

See **[TESTING.md](TESTING.md)** for the complete playbook (499 tests total).

## Files

| File | Purpose |
|------|---------|
| `PARITY.md` | R ↔ Python feature parity reference |
| `DATA_PIPELINES.md` | Catalog of synthetic/ingress/edge scenarios × wrappers × R fields |
| `conftest.py` | Re-exports shared pytest helpers from `tests/` |
| `_synth.py` | Data generators + R-globalenv plumbing for the parity pipelines |
| `test_regression_exploration.py` | Control sweeps, `lmrob_m`, DCML, stepwise, linear test |
| `test_multivariate_exploration.py` | `cov_rob` dispatcher, Rocke, fastmve, both PCA wrappers |
| `test_dataset_workflows.py` | Fit appropriate model on each of the 20 datasets |
| `test_helpers_and_glm.py` | `invtr2`, `refine_sm`, ψ tuning, GLM on clinical datasets |
| `test_combinatorial_matrix.py` | Cross-products: dataset×family×estimator, cov grids, method chains, stretch |
| `test_synthetic_pipelines.py` | numpy-RNG synthetic data → every wrapper, full-field strict R parity |
| `test_data_ingress.py` | CSV / sklearn / cross-package / pandas-wrangle ingress → R parity |
| `test_edge_cases.py` | Degenerate inputs fail cleanly or match R exactly |
| `TESTING.md` | Full testing playbook for the whole repo |

## Relation to `tests/` vs `docs/examples/`

- `tests/` — strict regression gate (`atol=0, rtol=0` vs R); CI-oriented.
- `docs/examples/` — five minimal runnable scripts for documentation.
- `exploration/` — **playground** for parameter grids, textbook reproductions,
  and discovering gaps before promoting cases into `tests/` or `docs/examples/`.
