# WMLlogreg (alias logregWML)

## 1. Statistical purpose
**Weighted Maximum-Likelihood robust logistic regression**. Maronna et al. (2019, §7.2). Treats leverage outliers by attaching MCD-derived weights to a standard MLE; simpler than the BY family and competitive for moderate contamination.

## 2. Mathematical background
Standard logistic MLE on the weighted log-likelihood, with weights from a robust covariance of the design matrix (MCD).

## 3. R implementation
- File: `robstattm/RobStatTM-master/R/WMLlogreg.R` line 34.
- Initial: `robustbase::covMcd` (line 80).

## 4. Inputs / Outputs / Return structure
**Signature:** `WMLlogreg(x0, y, intercept=1)`

Returns list with `coefficients`, `standard.errors`, `fitted.values`, `iter`, `convergence`.

## 5. Dependencies
- RobStatTM
- robustbase

## 6. Python wrapper design

```python
def wml_logreg(
    X: ArrayLike, y: ArrayLike, *, intercept: bool = True,
) -> LogregResult: ...
```

Returns the shared `LogregResult` dataclass.

## 7. Validation strategy
Cases 1, 2, 7, 10 + GLM cases 15, 16. Same fixture as `by_logreg`.
