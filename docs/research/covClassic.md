# covClassic

## 1. Statistical purpose
**Classical (Pearson) sample mean and covariance** wrapped to return the same S3 shape as `covRobMM`/`covRobRocke`. Used as the **non-robust baseline** in distance–distance plots and side-by-side comparisons.

## 2. Mathematical background
Trivial: sample mean and unbiased sample covariance.

## 3. R implementation
File: `Multirobu.R` line 725. Returns an S3 list of class `covClassic` with fields `center`, `cov`, `dist`, `cor`. Companion `summary.covClassic` (line 821) and `print.summary.covClassic` (line 840).

## 4. Inputs / Outputs / Return structure
`covClassic(data, corr=FALSE, center=TRUE, distance=TRUE, ...)` → list with `center`, `cov`, `cor` (if `corr`), `dist` (Mahalanobis if `distance=TRUE`), `n.obs`.

## 5. Dependencies
RobStatTM only (uses only base R).

## 6. Python wrapper design
```python
def cov_classic(
    X: ArrayLike, *, corr: bool = False, center: bool = True, distance: bool = True,
) -> CovClassicResult: ...
```
Returns the **same `CovRobResult`-shaped dataclass** as the robust variants, with an added `classical: bool = True` flag so `distance_distance(robust, classical)` works generically.

## 7. Validation strategy
Cases 1, 2, 7. Trivial to validate — bit-for-bit against `numpy.cov(ddof=1)`.
