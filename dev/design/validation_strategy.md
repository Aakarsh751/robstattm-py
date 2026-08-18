# Validation Strategy

**Core invariant:** for every wrapper output field, a `robstattm_py` call and a same-input, same-seed direct R call must produce values whose maximum absolute difference is **exactly zero**.

The proposal (§6, §9.1) sets this expectation and the existing notebook (`robstattm/python/robstatpy_comparison_rpy2.ipynb`) demonstrates it for `locScaleM` and `mScale` (14/14 checks pass with zero numerical difference). This document scales that policy to the full target set.

---

## 1. Numerical comparison policy

### 1.1 Tolerance tiers

| Tier | atol | rtol | Used for | Rationale |
|------|------|------|----------|-----------|
| **Strict** (default) | `0.0` | `0.0` | All scalar/array outputs of rpy2 wrappers vs. direct R calls | Same R code path executes; no floating-point reordering happens between Python and R; zero diff is the proven achievable bar |
| **Stable** | `1e-12` | `1e-12` | Outputs that pass through one extra rpy2 conversion (e.g. R `numeric()` → `np.float64` → `np.array`) where bit-for-bit equality is platform-dependent | A few `pcaRobS` paths re-coerce on the way back; allows safety margin without hiding bugs |
| **Algorithmic** | `1e-8` | `1e-6` | Native-Python re-implementations (Phase 6 stretch only) vs. R | Different IRLS schedules will not match bit-for-bit; this tier asserts statistical equivalence |
| **Plot** | `1e-3` (image-norm) | n/a | PNG regression tests for figures | Anti-alias / DPI noise |

**Default for the wrapper test suite is Strict.** Any test that needs Stable or above must document why on the assertion line:

```python
np.testing.assert_allclose(py.coefficients, r_coef, atol=1e-12, rtol=1e-12,
    err_msg="coefficients pass through pandas2ri float64 coercion; strict tier impossible on Windows")
```

### 1.2 Comparison primitives

| Field type | Function | Notes |
|------------|----------|-------|
| Scalar float | `assert py == r` (strict) or `math.isclose` (stable) | NaN compared with `math.isnan(py) and math.isnan(r)` |
| 1-D float array | `np.testing.assert_array_equal` (strict) / `assert_allclose` (stable) | Length checked first |
| 2-D float matrix | `np.testing.assert_array_equal` | Shape checked; symmetric matrices verified for symmetry first |
| Integer | `assert py == r` | rpy2 maps `integer` correctly |
| Logical | `assert bool(py) is bool(r)` |  |
| String / factor | `assert py == r` | Factor levels also checked |
| Nested R list | Recursively unpack via the dataclass's field map; compare leaves | Per-field error message |

A helper in `tests/conftest.py`:

```python
def assert_r_equal(py_result, r_result, tier="strict"):
    """Field-by-field comparison of a dataclass against an R list."""
    for field in py_result.__dataclass_fields__:
        py_val = getattr(py_result, field)
        r_val  = r_result.rx2(_field_map_py_to_r[field])
        _assert_eq(py_val, r_val, tier=tier, where=field)
```

---

## 2. Randomness and reproducibility

### 2.1 The cross-language seed problem

- `set.seed(n)` in R initializes R's Mersenne-Twister state.
- `np.random.seed(n)` initializes NumPy's separate MT state.
- They are **independent**: setting one does not affect the other.

For wrappers, only R-side randomness matters (the R code does the simulation). For tests that generate synthetic data **in Python** and then call a wrapper, both seeds matter because the data crosses the bridge.

### 2.2 Seed policy

- All randomness goes through `robstattm_py.set_seed(n)`. It calls **both** `np.random.seed(n)` and `R("set.seed(%d)" % n)` in that order.
- Every test that touches randomness opens with `set_seed(20260601)` (or another fixed integer). The integer **is part of the test** and never read from the clock.
- For wrappers whose R implementation calls `set.seed` internally with a fixed value (e.g. some bootstrap helpers), document this in the wrapper docstring and **do not** override it in the test fixture.
- The `pyinit` wrapper takes an explicit `seed` argument and forwards it to the R call; tests assert that two calls with the same seed return bit-identical results.

### 2.3 Cross-language reproducibility recipe (drafted)

```python
import robstattm_py as rpm
import numpy as np
from robstattm_py import set_seed

def golden_dataset_1():
    set_seed(20260601)
    n, p = 200, 5
    X = np.random.randn(n, p)
    eps = np.random.randn(n)
    y = X @ np.arange(1, p+1) + eps
    # contaminate 5%
    out_idx = np.random.choice(n, size=int(0.05*n), replace=False)
    y[out_idx] += 10
    return X, y
```

The same data, when regenerated in R via the analogous `set.seed(20260601); ...` script, must produce a bit-identical `X, y, out_idx`. This is the precondition for strict-tier wrapper validation.

---

## 3. Testing matrix

For **every** wrapper, the following test cases exist:

| # | Case | What it asserts |
|---|------|-----------------|
| 1 | Textbook example (golden dataset from `robstattm/examples-scripts/`) | Strict-tier match against the published R output values stored as fixtures |
| 2 | Small synthetic clean (n=50, p=3, no contamination) | Strict-tier match vs. fresh R call |
| 3 | Small synthetic contaminated (n=50, p=3, 5% outliers at 10σ) | Strict-tier match vs. fresh R call |
| 4 | Medium synthetic contaminated (n=1000, p=20, 5%) | Strict-tier match vs. fresh R call |
| 5 | High-dimensional (n=500, p=50) | Strict-tier match; smoke-test for `covRobRocke` regime change |
| 6 | Missing values (NaN in inputs) | Either raises the same R error message (regression) or imputes identically (covariance with GSE/TSGS stretch) |
| 7 | Invalid input (wrong shape, string in numeric column) | Raises `TypeError` / `ValueError` **before** crossing rpy2, caught with `pytest.raises` |
| 8 | Empty input | Raises `ValueError` cleanly |
| 9 | Boundary tuning parameters (efficiency=0.85, 0.90, 0.95; bisquare, huber, mopt) | Each combination matches R |
| 10 | Repeatability under fixed seed (call twice → identical output) | Determinism check |
| 11 | (Where applicable) Repeatability under different seeds → different output | Sanity: the seed argument actually does something |

Phase-1 wrappers (`locScaleM`, `mScale`) inherit a smaller variant since they don't take formulas / matrices. Cases 1–4, 7–10 apply.

Phase-3 wrappers (covariance, PCA) add:

| # | Case | What it asserts |
|---|------|-----------------|
| 12 | Symmetry of covariance return | `assert_array_equal(C, C.T)` |
| 13 | Positive-semidefiniteness | All eigenvalues ≥ −1e-12 |
| 14 | Mahalanobis distance distribution under clean Gaussian | smoke-test only, not a hard assertion |

Phase-6 GLM wrappers add:

| # | Case | What it asserts |
|---|------|-----------------|
| 15 | Probability outputs in [0,1] | trivial |
| 16 | Convergence flag matches R | strict |

---

## 4. Coverage gate

- Tool: `pytest --cov=robstattm_py --cov-fail-under=90`.
- Branch coverage on. Coverage is enforced in CI on every push to `main` and every PR.
- The 90% figure is **per module** (univariate, regression, covariance, pca, glm), averaging hides under-tested modules.

---

## 5. CI integration

```
GitHub Actions
├── lint (ruff)                            # fast, runs first
├── unit-test matrix
│   ├── ubuntu-latest × Py 3.10 / 3.11 / 3.12 × R 4.3 / 4.4 / 4.5
│   ├── macos-latest  × Py 3.11           × R 4.4 / 4.5
│   └── windows-latest × Py 3.11          × R 4.4   (skip pyinit-only tests if binary unavailable)
├── coverage gate                          # depends on all unit-test jobs
└── docs-build (sphinx -W)                 # warnings = errors
```

Each unit-test job: install Python deps → install R + RobStatTM + pyinit + robustbase + rrcov → `pytest` → upload coverage artifact.

---

## 6. Golden fixtures

Each textbook example is encoded as a small R script that prints the expected return list as JSON via `jsonlite::toJSON(...)`. The JSON file is checked into `tests/fixtures/` and the wrapper test parses it. This avoids re-running R on every test invocation for the golden comparisons, while a separate "freshness" CI job re-runs the R scripts weekly to detect upstream RobStatTM changes.

```
tests/fixtures/
├── mineral_lmrobdetMM.json
├── wine_covRobMM.json
├── bus_pcaRobS.json
└── README.md   # explains how to regenerate via scripts/regenerate_fixtures.R
```

---

## 7. What this strategy does NOT cover

- Plot-image regression (covered separately in `project_memory/robstattm-py-planning-docs/plotting_strategy.md` and the `pytest-mpl` config).
- Benchmark *performance* targets (Phase 4 evaluates speed; no pass/fail gate other than "must complete within CI timeout").
- Native-Python (Phase 6 stretch) tests use the **Algorithmic** tier and live in `tests/native/`, they are not part of the ≥ 90 % coverage gate for the wrapper code.
