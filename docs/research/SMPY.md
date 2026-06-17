# SMPY

## 1. Statistical purpose
**S+M fit with Peña–Yohai split-sample initialization** — companion to `MMPY`. Exported helper used inside `lmrobdetDCML`'s pipeline.

## 2. R implementation
File: `DCML.R` line 307. Signature: `SMPY(mf, y, control, split)`.

## 3. Python wrapper design
```python
def smpy(
    mf: pd.DataFrame, y: ArrayLike, *,
    control: LmrobdetControl, split: ArrayLike,
) -> LmrobdetMMResult: ...
```
Same return shape as `mmpy`.

## 4. Validation strategy
Cases 1–3, 7, 10. Strict-tier against R.
