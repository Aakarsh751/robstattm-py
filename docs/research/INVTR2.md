# INVTR2

## 1. Statistical purpose
**Invariant robust $R^2$** — Maronna's preferred robust analogue of $R^2$ for robust regression fits. Computed inside `lmrobdetMM` and exposed separately so users can score fits they constructed by other means.

## 2. R implementation
File: `INVTR2.R`. Returns a scalar in $[0, 1]$.

## 3. Python wrapper design
```python
def invtr2(
    residuals: ArrayLike, y: ArrayLike, *, scale: float, control: LmrobdetControl,
) -> float: ...
```

## 4. Validation strategy
Cases 1, 2, 7, 10. Strict-tier scalar match. Also unit-test that `lmrobdet_mm(...).r_squared == invtr2(fit.residuals, y, scale=fit.scale, control=fit.control)`.
