# pense (external R package — IMPLEMENTED 2026-06-13)

> **Status (2026-06-13):** implemented against the *installed* pense **2.5.2**,
> whose API differs from the older CRAN docs this file originally described.
> `rpm.pense` / `rpm.pense_cv` ship in `robstatm_py.external`, 100% strict-tier
> vs R (`tests/external/test_pense.py`). The "Actual implementation" section at
> the bottom is authoritative; the older design notes are kept for provenance.

## 1. Statistical purpose
**Robust elastic-net S-estimator** for linear regression. Generalizes MM-lasso to the elastic-net penalty, retaining high breakdown while performing variable selection. Maronna et al. (2019, §5.1).

## 2. Mathematical background
Minimizes a robust scale of residuals plus an elastic-net penalty $\alpha \|\beta\|_1 + (1-\alpha)/2 \|\beta\|_2^2$. Uses a Peña–Yohai-style initial grid + coordinate descent.

## 3. R implementation
- **External CRAN package** `pense`. Not in this repo.
- Main entry point (per CRAN): `pense(x, y, alpha, nlambda=50, ...)`; companion `pense_cv`, `pensem` (MM extension), `mloc` / `mscale` helpers.
- Heavy Rcpp + Eigen backend.

## 4. Inputs / Outputs / Return structure
Returns an S3 list of class `"pense"` with `coefficients` (sparse matrix across the lambda path), `lambda`, `alpha`, `objective_F`, `metrics`, plus CV fields if `pense_cv`.

## 5. Dependencies
- pense
- transitive: Rcpp, RcppArmadillo

## 6. Python wrapper design

```python
def pense(
    X: ArrayLike, y: ArrayLike,
    *,
    alpha: float = 0.5,
    nlambda: int = 50,
    lambda_path: ArrayLike | None = None,
    standardize: bool = True,
    intercept: bool = True,
    bdp: float = 0.25,
    cv: bool = False,
    cv_k: int = 5,
    seed: int | None = None,
) -> PenseResult: ...
```

```python
@dataclass(frozen=True, slots=True)
class PenseResult:
    coefficients: scipy.sparse.csr_matrix   # (p+1) × n_lambda (intercept row 0)
    lambdas: np.ndarray
    alpha: float
    objective_f: np.ndarray
    cv_curve: np.ndarray | None
```

Output uses `scipy.sparse` because pense paths are typically very sparse and full-dense storage is wasteful at large $p$.

## 7. Validation strategy
Cases 1–4, 7, 10. Reproduce one published `pense` example (e.g., the package vignette). **Optional in v0.1.0** per blocker B-006.

---

## Actual implementation (pense 2.5.2, 2026-06-13)

**Module:** `robstatm_py.external.pense` — exposed as `rpm.pense`, `rpm.pense_cv`.

### `pense(X, y, *, alpha=0.5, nlambda=50, bdp=0.25, intercept=True, standardize=True) -> PenseResult`

R object `pense::pense` (class `pense, pense_fit`) has slots
`call, bdp, lambda, metrics, estimates, alpha`. There is **no** ready coefficient
matrix; coefficients come from the S3 method `coef(fit, lambda=L)` (named
length-(p+1) numeric). The wrapper builds the full matrix in R:
`sapply(fit$lambda[[1]], \(L) as.numeric(coef(fit, lambda=L)))`.

```python
@dataclass(frozen=True, slots=True)
class PenseResult:
    coefficients: np.ndarray      # (p+1, n_lambda); row 0 = intercept
    intercepts:   np.ndarray      # (n_lambda,)  = coefficients[0]
    slopes:       np.ndarray      # (p, n_lambda) = coefficients[1:]
    coef_names:   tuple[str, ...] # ("(Intercept)", "X1", ...)
    lambda_path:  np.ndarray      # fit$lambda[[1]]
    alpha:        float
    bdp:          float
```

### `pense_cv(X, y, *, alpha=0.5, nlambda=50, bdp=0.25, cv_k=5, cv_repl=1, ...) -> PenseCVResult`

```python
@dataclass(frozen=True, slots=True)
class PenseCVResult:
    coef_min:    np.ndarray       # coef(fit, lambda="min")
    coef_names:  tuple[str, ...]
    lambda_min:  float
    lambda_path: np.ndarray
    cv_avg:      np.ndarray       # cvres$cvavg
    cv_se:       np.ndarray       # cvres$cvse
    cvres:       pd.DataFrame     # full R cvres table
    alpha:       float
    bdp:         float
```

### Implementation notes (see decisions.md D-018, discoveries.md 2026-06-13)
- **Fit in R-space.** Holding the fit in Python and pushing it to `globalenv`
  strips its S3 class → `coef()` mis-dispatches. So we push X/y and run
  `ro.r("fit <- pense::pense(...)")`.
- **Avoid converting the cvfit.** Its embedded data.frames crash the active
  numpy/pandas converter. Fit statement ends `; 0L`; `_r_fit` is fetched under
  `default_converter`; `cvres` is rebuilt column-by-column.
- **Stochastic** (PY initials) → call `rpm.set_seed(n)` before for reproducibility.

### Validation
`tests/external/test_pense.py`: lambda path, full coefficient matrix, intercept/
slope views, alpha/bdp, coef names, CV coef_min, cv_avg/cv_se, lambda_min, cvres
columns, `to_dict`. All strict-tier (atol=0, rtol=0). Auto-skips via `needs_pense`.
