# pyinit (external R package)

## 1. Statistical purpose
**Peña–Yohai highly robust initial estimator** for high-breakdown regression. The default initialization used by `lmrobdetMM` and `lmrobdetDCML`. Maronna et al. (2019, §5.7).

## 2. Mathematical background
Constructs many candidate initial regressions by iterated principal-sensitivity selection (Peña & Yohai 1999), keeping the candidate with the smallest robust scale. Designed to escape local optima of the S-objective.

## 3. R implementation
- **External** CRAN package `pyinit`. Not in the RobStatTM repo.
- Called from `robstattm/RobStatTM-master/R/DCML.R:165` and `:333`.
- API — verified against the installed package via `formals(pyinit::pyinit)`
  (NOT an outdated CRAN doc; argument names use **underscores**, and several
  defaults differ from older write-ups):
  `pyinit(x, y, intercept=TRUE, delta=0.5, cc, maxit=10, psc_keep, resid_keep_method=c("threshold","proportion"), resid_keep_prop, resid_keep_thresh, eps=1e-8, mscale_maxit=200, mscale_tol=eps, mscale_rho_fun="bisquare")`
- `resid_keep_method` defaults to `"threshold"` (the first `match.arg` value),
  `maxit=10`, `eps=1e-8`, and `mscale_tol` defaults to `eps`.
- **Deterministic:** no `nsamp`/seed argument; repeated calls on the same input
  are `identical()`. No seeding is required for reproducibility.

## 4. Inputs / Outputs / Return structure
Returns a list with `coefficients` (matrix; columns are candidate solutions), `objective` (vector of objective values), `best.beta`, and convergence info.

## 5. Dependencies
- pyinit (CRAN)
- RobStatTM not required at the function level, but the wrapper lives in `robstattm_py.regression.pyinit` because users encountering it from `lmrobdetMM` will look there.

## 6. Python wrapper design

```python
def pyinit(
    X: ArrayLike,
    y: ArrayLike,
    *,
    intercept: bool = True,
    delta: float = 0.5,
    cc: float = 1.5476,
    psc_keep: float = 0.5,
    resid_keep_method: Literal["threshold", "proportion"] = "threshold",
    resid_keep_prop: float = 0.2,
    resid_keep_thresh: float = 2.0,
    maxit: int = 10,
    eps: float = 1e-8,
    mscale_maxit: int = 200,
    mscale_tol: float | None = None,   # None -> R's default (= eps)
    mscale_rho_fun: Literal["bisquare", "huber", "gauss"] = "bisquare",
) -> PyinitResult: ...
```

Defaults mirror `formals(pyinit::pyinit)` exactly so `rpm.pyinit(X, y)` reproduces
`pyinit::pyinit(x, y)`. `pyinit` is deterministic, so no `seed` kwarg is needed.

## 7. Validation strategy
Cases 1–4, 7, 10. **Windows skip path:** if `pyinit` is not installable on the runner, mark the entire test module `pytest.skip("pyinit not available on this platform")` with a clear message — do not let it fail the build. Tracked as B-003 in `project_memory/blockers.md`.
