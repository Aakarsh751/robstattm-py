# covRob (generic dispatcher)

## 1. Statistical purpose
**High-level entry point** for robust covariance: chooses `covRobRocke` when $p \ge 10$, `covRobMM` otherwise. Aligned with the book's recommendation (Maronna et al. 2019 §6.5 vs §6.4).

## 2. Mathematical background
Pure dispatch; no estimation of its own.

## 3. R implementation
File: `Multirobu.R` line 56-57. Top of file:
```r
if (p >= 10) resu = RockeMulti(X, ...) else resu = MMultiSHR(X, ...)
```

## 4. Inputs / Outputs / Return structure
`covRob(X, type = c("auto","MM","Rocke"), corr=FALSE, ...)` → same `covRob` S3 list.

## 5. Dependencies
RobStatTM only (transitively whichever sub-estimator runs).

## 6. Python wrapper design
```python
def cov_rob(
    X: ArrayLike, *,
    type: Literal["auto","MM","Rocke"] = "auto",
    corr: bool = False,
    **kwargs,
) -> CovRobResult: ...
```
`**kwargs` forwarded to `cov_rob_mm` or `cov_rob_rocke` depending on dispatch. Returns the shared `CovRobResult` dataclass; sets `.method = "MM" | "Rocke"` so the caller can see which path was taken.

## 7. Validation strategy
Cases 1–5 with `type="auto"`, plus a dispatch-correctness test: $p=8$ → MM; $p=12$ → Rocke.
