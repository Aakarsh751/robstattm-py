# prcompRob

## 1. Statistical purpose
A **`prcomp`-shaped wrapper** around `pcaRobS`. Same return shape as base R `prcomp`: components named `sdev`, `rotation`, `x` (scores), `center`. Drop-in replacement for users porting `prcomp(...)` code.

## 2. Mathematical background
Identical to `pcaRobS`; only the return shape differs.

## 3. R implementation
File: `prcompRob.R` line 34. S3 class `prcompRob` with `print.prcompRob`, `summary.prcompRob`, `print.summary.prcompRob`.

## 4. Inputs / Outputs / Return structure
`prcompRob(x, rank.=NULL, delta.scale=0.5, max.iter=100L)` → S3 list with `sdev`, `rotation`, `center`, `x`.

## 5. Dependencies
RobStatTM + rrcov (via the inner `pcaRobS`).

## 6. Python wrapper design
```python
def prcomp_rob(
    X: ArrayLike, *, rank_: int | None = None,   # R: rank.
    delta_scale: float = 0.5, max_iter: int = 100,
) -> PrcompRobResult: ...
```
```python
@dataclass(frozen=True, slots=True)
class PrcompRobResult:
    sdev: np.ndarray
    rotation: np.ndarray         # (p, k) loadings (R-shaped)
    center: np.ndarray
    scores: np.ndarray           # R: x  — renamed for clarity
    def summary(self) -> SummaryTable: ...
```

## 7. Validation strategy
Cases 1–4, 7, 10 plus equality with `pca_rob_s` outputs (just a different return shape).
