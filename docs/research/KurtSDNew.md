# KurtSDNew (alias initPP)

## 1. Statistical purpose
**Peña–Prieto highly robust initial estimator** of multivariate location and shape, driven by **kurtosis maximization/minimization** over random projection directions. Used as the default initial covariance for `covRobMM` and `covRobRocke`. Maronna et al. (2019, §6.9.2).

## 2. Mathematical background
Searches over projection directions for those that maximize / minimize kurtosis; outlier directions cluster at the kurtosis extremes. The resulting location/shape estimate has high breakdown.

## 3. R implementation
- File: `robstattm/RobStatTM-master/R/KurtSDNew.R` line 40.
- Internal: `KurNwm`, `MaxKur`, `MinKur`, `SdwDir`, `ValKur`.

## 4. Inputs / Outputs / Return structure
**Signature:** `KurtSDNew(X, muldirand=20, muldifix=10, dirmin=1000)`

Returns a list with `center`, `cov` (shape), `dist` plus diagnostic fields.

## 5. Dependencies
- RobStatTM only.

## 6. Python wrapper design

```python
def kurt_sd_new(
    X: ArrayLike,
    *,
    muldirand: int = 20,
    muldifix: int = 10,
    dirmin: int = 1000,
    seed: int | None = None,
) -> KurtSDResult: ...
```

`seed` is required for reproducibility because the routine samples random directions; pass-through to `set_seed`.

```python
@dataclass(frozen=True, slots=True)
class KurtSDResult:
    center: np.ndarray
    cov: np.ndarray
    dist: np.ndarray
```

## 7. Validation strategy
Cases 1–4, 7, 10. Determinism (case 10) under a fixed seed is essential — without it, the algorithm's randomness will produce non-reproducible output across runs.
