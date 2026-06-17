# covRobMM (alias MMultiSHR)  **(critical)**

## 1. Statistical purpose
**MM-estimator of multivariate location and covariance** using the SHR ρ family. Recommended for moderate-dimensional data ($p < 10$) in Maronna et al. (2019, §6.5). Robust to up to ~50% contamination while maintaining good Gaussian efficiency.

## 2. Mathematical background
S step (Smoothed Hard-Rejection ρ) initialized via `KurtSDNew`, refined to MM efficiency. Returns center, covariance, robust distances (Mahalanobis), and case weights.

## 3. R implementation
- File: `robstattm/RobStatTM-master/R/Multirobu.R` line 352.
- Internal: `MscalSHR` (line 401), `meanrhoSHR`, `rhoSHR`, `weightsSHR`, `consMMKur` (constant calibration), `mahdist`.

## 4. Inputs / Outputs / Return structure
**Signature:** `covRobMM(X, maxit=50, tolpar=1e-4, corr=FALSE)`

Returns S3 list of class `"covRob"`: `center`, `cov`, `dist` (squared Mahalanobis), `wts` (case weights), `mu0`/`V0` (initial), `iter`, `converged`, `cor` (when `corr=TRUE`).

## 5. Dependencies
- RobStatTM
- robustbase (Mahalanobis utilities)

## 6. Python wrapper design

```python
def cov_rob_mm(
    X: ArrayLike,             # (n, p)
    *,
    maxit: int = 50,
    tolpar: float = 1e-4,
    corr: bool = False,
) -> CovRobResult: ...
```

```python
@dataclass(frozen=True, slots=True)
class CovRobResult:
    center: np.ndarray         # (p,)
    cov: np.ndarray            # (p, p)
    dist: np.ndarray           # (n,) squared Mahalanobis
    wts: np.ndarray            # (n,)
    iter: int
    converged: bool
    cor: np.ndarray | None = None
```

**Edge cases:** singular covariance (rank-deficient X); $n \le p$.

## 7. Validation strategy
All 11 cases plus 12 (symmetry) and 13 (PSD) from `docs/validation_strategy.md §3`. Reproduce `wine.R` (Fig 6.3). The existing notebook already validates `covRobMM` — port that fixture.
