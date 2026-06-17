# lmrobM

## 1. Statistical purpose
Robust M-estimator for linear regression with **designed (low-leverage) experiments**, where high-breakdown initialization is not required. Maronna et al. (2019, §4.4) recommends `lmrobM` when the design matrix is fixed and there is no concern about leverage outliers.

## 2. Mathematical background
IRLS on a monotone or re-descending $\psi$ family with a separately-supplied or robust scale estimate. Unlike MM, there is no S-estimator initialization; the algorithm starts from LS or a user-supplied beta0.

## 3. R implementation
- File: `robstattm/RobStatTM-master/R/lmrobdet.R` line 1184.
- Control object: `lmrobM.control` at line 1468.
- Calls `robustbase::robMD` for robust Mahalanobis distance in leverage diagnostics.

## 4. Inputs / Outputs / Return structure
**Signature:** `lmrobM(formula, data, subset, weights, na.action, control=lmrobM.control(...), ...)`

Returns an S3 list of class `"lmrob"` with the usual fields: `coefficients`, `scale`, `residuals`, `fitted.values`, `weights`, `rweights`, `rank`, `df.residual`, `cov`, `qr`, `iter`, `converged`, `MD` (robust Mahalanobis distances).

## 5. Dependencies
- RobStatTM
- robustbase (via `robMD`)

## 6. Python wrapper design

```python
def lmrob_m(
    formula: FormulaLike,
    data: pd.DataFrame,
    *,
    control: LmrobMControl | None = None,
    weights: ArrayLike | None = None,
    subset: ArrayLike | None = None,
    na_action: Literal["omit","fail","pass"] = "omit",
) -> LmrobMResult: ...
```

Field map: `fitted.values`→`fitted_values`, `r.squared`→`r_squared`, `df.residual`→`df_residual`, `MD`→`md`.

**Edge cases:** singular design matrix; perfectly fitting data.

## 7. Validation strategy
Cases 1, 2, 3, 4, 7, 9, 10. Reproduce `oats.R` and `algae.R` examples from `robstattm/examples-scripts/` as golden fixtures.
