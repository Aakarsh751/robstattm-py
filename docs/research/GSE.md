# GSE (external R package — IMPLEMENTED 2026-06-13)

> **Status (2026-06-13):** implemented against installed GSE **4.2-4** as
> `rpm.gse` in `robstattm_py.external`. The R object is **S4** (not the S3 list
> this file first guessed). 100% strict-tier vs R (`tests/external/test_gse.py`).
> See "Actual implementation" at the bottom.

## 1. Statistical purpose
**Generalized S-Estimator** of multivariate location and covariance with **missing data**. Maronna et al. (2019, §6.12.2). Robust to row-wise outliers while properly handling MAR missingness.

## 2. Mathematical background
EM-style iteration alternating between (1) imputing missing entries under the current robust shape and (2) re-fitting an S-estimator on the completed data. Convergence to a robust analogue of the EM-MLE.

## 3. R implementation
- **External CRAN package** `GSE`. Not in this repo.
- Main entry point: `GSE(x, ...)` returning an S4 object of class `"GSE"`.

## 4. Inputs / Outputs / Return structure
S4 object with slots: `mu`, `S` (covariance), `weights`, `iter`, `convergence`, `xmiss` (imputed matrix), `pmd` (partial Mahalanobis distance).

## 5. Dependencies
- GSE
- transitive: ggplot2 (light), MASS

## 6. Python wrapper design

```python
def gse(
    X: ArrayLike,                     # missing entries as NaN
    *,
    tol: float = 1e-4,
    maxiter: int = 150,
    method: Literal["bisquare","rocke"] = "bisquare",
    init: Literal["emve","huber"] = "emve",
) -> GSEResult: ...
```

```python
@dataclass(frozen=True, slots=True)
class GSEResult:
    mu: np.ndarray
    cov: np.ndarray           # S slot
    weights: np.ndarray
    iter: int
    converged: bool
    imputed: np.ndarray       # xmiss
    pmd: np.ndarray
```

S4-to-Python conversion happens via `rpy2`'s S4 facilities (`.slots`).

## 7. Validation strategy
Cases 1, 2, 6 (missing values is the **whole point** of this wrapper), 7, 10. Build a synthetic MAR test (mask 10% of entries randomly with a fixed seed).

---

## Actual implementation (GSE 4.2-4, 2026-06-13)

**Module:** `robstattm_py.external.gse` — exposed as `rpm.gse`.

`GSE::GSE(x, tol=1e-4, maxiter=150, method="bisquare", ...)` returns an **S4**
object (class `GSE`) with slots
`mu0, S0, weights, weightsp, ximp, iter, eps, sc, mu, S, call, estimator, x,
pmd, pmd.adj, p, pu`. rpy2 reads slots via `obj.slots["mu"]`. Verified the public
accessors equal the slots: `getLocation(g)==g@mu`, `getScatter(g)==g@S`,
`getDist(g)==g@pmd`.

```python
@dataclass(frozen=True, slots=True)
class GSEResult:
    mu:       np.ndarray   # slot mu      (== getLocation)
    cov:      np.ndarray   # slot S       (== getScatter)
    pmd:      np.ndarray   # slot pmd     (== getDist), partial Mahalanobis^2
    pmd_adj:  np.ndarray   # slot pmd.adj
    weights:  np.ndarray   # slot weights
    ximp:     np.ndarray   # slot ximp, imputed data
    sc:       float        # slot sc, generalized S-scale
    iter:     int
    eps:      float
    column_names: tuple[str, ...] | None
```

### Notes
- **Missing data is the point**: `X` may contain NaN. `validate_2d_numeric(...,
  allow_nan=True)` permits NaN; Inf is still rejected.
- **Stochastic** (EMVE init) → `rpm.set_seed(n)` before for reproducibility.

### Validation
`tests/external/test_gse.py::TestGSE`: mu, cov, pmd, pmd_adj, weights, ximp, sc,
iter, symmetry, accessor-equals-slot. Strict-tier; auto-skips via `needs_gse`.
