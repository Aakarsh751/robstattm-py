# lmrobdetDCML

## 1. Statistical purpose
**Distance-constrained MLE** robust regression. Boosts efficiency over plain MM by combining an MM fit (high breakdown) with a constrained MLE step that recovers efficiency near 100% under Gaussian errors while preserving the MM breakdown point. Maronna et al. (2019, §5.9).

## 2. Mathematical background
DCML minimizes the LS objective subject to a robust-distance constraint between $\beta$ and the MM-estimate, yielding $\beta^{\text{DCML}}$ that is closer to LS when the data are clean and snaps back to MM when contaminated.

## 3. R implementation
- File: `robstattm/RobStatTM-master/R/DCML.R` line 255 (`DCML`) and line 876 of `lmrobdet.R` (`lmrobdetDCML` user-facing function).
- Helpers in `DCML.R`: `cov.dcml` (line 112), `MMPY` (line 154), `SMPY` (line 307).
- Hard dependency on `pyinit::pyinit` at lines 165 and 333.

## 4. Inputs / Outputs / Return structure
**Signature:** `lmrobdetDCML(formula, data, subset, weights, na.action, control=lmrobdet.control(...), ...)`

Returns an S3 object similar to `lmrobdetMM` plus DCML-specific fields: `beta.MM`, `beta.DCML`, `dist` (distance), `tau`.

## 5. Dependencies
- RobStatTM
- pyinit (**hard**)
- robustbase

## 6. Python wrapper design

```python
def lmrobdet_dcml(
    formula: FormulaLike,
    data: pd.DataFrame,
    *,
    control: LmrobdetControl | None = None,
    weights: ArrayLike | None = None,
    subset: ArrayLike | None = None,
    na_action: Literal["omit","fail","pass"] = "omit",
) -> LmrobdetDCMLResult: ...
```

Dataclass mirrors `LmrobdetMMResult` plus `beta_mm`, `beta_dcml`, `dist`, `tau`.

## 7. Validation strategy
Cases 1–4, 7, 10. Hard skip on platforms without `pyinit` (matches B-003).
