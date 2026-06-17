# lmrobdetMM.RFPE

## 1. Statistical purpose
**Robust Final Prediction Error** score for an existing `lmrobdetMM` fit. The model-selection criterion used by `step.lmrobdetMM`. Maronna et al. (2019, §5.6).

## 2. R implementation
Files: `RFPE.R` (RFPE computation). Returns a scalar.

## 3. Python wrapper design
```python
def lmrobdet_mm_rfpe(fit: LmrobdetMMResult) -> float: ...
```

Also exposed as a **method**: `fit.rfpe()` returning the same scalar.

## 4. Validation strategy
Cases 1, 2, 7, 10. Strict-tier scalar match.
