# covRobRocke (alias RockeMulti)  **(critical)**

## 1. Statistical purpose
**Rocke's S-estimator** for multivariate location and covariance. Recommended for **higher-dimensional** data ($p \ge 10$) in Maronna et al. (2019, §6.4.2, §6.4.4) where the standard bisquare S-fit degrades.

## 2. Mathematical background
Uses Rocke's translated-truncated-loss ρ that scales gracefully with $p$ (constant `gamma` tuned by `consRocke`). Reference: Rocke (1996).

## 3. R implementation
- File: `robstattm/RobStatTM-master/R/Multirobu.R` line 114 (`RockeMulti` / `covRobRocke`).
- Internal: `consRocke` (line 195/574), `WRoTru`, `rhorotru`, `MScalRocke`, `desceRocke` (line 512).
- Default initial estimator: `K` (Peña–Prieto Kurtosis-SD; see `KurtSDNew`).

## 4. Inputs / Outputs / Return structure
**Signature:** `covRobRocke(X, initial='K', maxsteps=5, propmin=2, qs=2, maxit=50, tol=1e-4, corr=FALSE)`

Returns the same shape as `covRobMM` (S3 `covRob`): `center`, `cov`, `dist`, `wts`, `iter`, `converged`, `cor`.

## 5. Dependencies
- RobStatTM only (the Kurtosis-SD initial is internal).

## 6. Python wrapper design

```python
def cov_rob_rocke(
    X: ArrayLike,
    *,
    initial: Literal["K","mve"] = "K",
    maxsteps: int = 5,
    propmin: float = 2,
    qs: float = 2,
    maxit: int = 50,
    tol: float = 1e-4,
    corr: bool = False,
) -> CovRobResult: ...
```

Returns the same `CovRobResult` dataclass as `cov_rob_mm` (`docs/research/covRobMM.md`). One dataclass for both means an integration helper (e.g. `distance_distance(rocke, classical)`) handles both transparently.

## 7. Validation strategy
All 11 cases + 12 (symmetry) + 13 (PSD). High-dimensional case (`n=500, p=50`) is especially relevant for verifying the Rocke regime.
