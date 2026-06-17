# MMPY

## 1. Statistical purpose
**MM-fit with Peña–Yohai initialization** — used internally by `lmrobdetMM` and exported for users who want the MM fit on a pre-prepared `(X, y)` without the formula interface.

## 2. R implementation
File: `DCML.R` line 154. Signature: `MMPY(X, y, control, mf)`. Calls `pyinit::pyinit` internally.

## 3. Python wrapper design
```python
def mmpy(
    X: ArrayLike, y: ArrayLike, *,
    control: LmrobdetControl | None = None,
    mf: pd.DataFrame | None = None,
) -> LmrobdetMMResult: ...
```
Returns the same `LmrobdetMMResult` as `lmrobdet_mm`.

## 4. Dependencies
RobStatTM + pyinit + robustbase.

## 5. Validation strategy
Cases 1–4, 7, 10. Strict-tier against `lmrobdet_mm` on the same `(X, y)`.
