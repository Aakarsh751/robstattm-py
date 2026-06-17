# fastmve

## 1. Statistical purpose
**Fast Minimum Volume Ellipsoid** robust initial covariance estimator. Used internally as an option for `covRobRocke` initialization (`initial="mve"`) and exported so users can call it directly.

## 2. Mathematical background
MVE: find the ellipsoid of minimum volume containing $\lceil(n+p+1)/2\rceil$ observations. C-implemented (`src/fastmve.c`) for speed.

## 3. R implementation
File: `fastmve.R` — exports `fastmve(x, nsamp=500)`. Backed by `src/fastmve.c`.

## 4. Inputs / Outputs / Return structure
`fastmve(x, nsamp=500)` → list with `center`, `cov`, `best` (subset indices).

## 5. Dependencies
RobStatTM only.

## 6. Python wrapper design
```python
def fastmve(X: ArrayLike, *, nsamp: int = 500, seed: int | None = None) -> FastMVEResult: ...
```
Random subsampling → `seed` required for reproducibility.

```python
@dataclass(frozen=True, slots=True)
class FastMVEResult:
    center: np.ndarray
    cov: np.ndarray
    best: np.ndarray   # 1-based in R; 0-based in Python (documented)
```

## 7. Validation strategy
Cases 1–4, 7, 10. **Note** the 1-based → 0-based index conversion in `best` — `tests/covariance/test_fastmve.py` must test both that the indices are 0-based and that they round-trip through `data.iloc[best]` correctly.
