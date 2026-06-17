# DCML (low-level)

## 1. Statistical purpose
The **core DCML estimator** that `lmrobdetDCML` wraps. Exported so power users can call DCML on pre-prepared design matrices without the formula interface.

## 2. R implementation
File: `DCML.R` line 255. Signature: `DCML(x, y, z, z0, control)` where `z` and `z0` are pre-computed initial estimates.

## 3. Python wrapper design
```python
def dcml(
    X: ArrayLike, y: ArrayLike,
    *,
    z: ArrayLike,            # initial estimate (usually from MMPY)
    z0: ArrayLike,           # alternative initial
    control: LmrobdetControl | None = None,
) -> DCMLResult: ...
```
Most users will reach for `lmrobdet_dcml` instead; `dcml` is the bare-metal hook.

## 4. Validation strategy
Cases 1–3, 7, 10. Internal consistency: `lmrobdet_dcml(formula, data)` and a hand-built `dcml(X, y, z, z0, control)` on the same data must produce strict-tier identical output.
