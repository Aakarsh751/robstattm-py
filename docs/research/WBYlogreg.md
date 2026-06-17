# WBYlogreg (alias logregWBY)

## 1. Statistical purpose
**Weighted Bianco–Yohai redescending M-estimator** for logistic regression. The **primary GLM recommendation** in Maronna et al. (2019, §7.2). Improves on `BYlogreg` by adding weights that bound the influence of high-leverage observations.

## 2. Mathematical background
Adds carrier-space weights derived from a robust covariance estimate (`covMcd`) so that the M-estimating equation is bounded simultaneously in residual space and design space.

## 3. R implementation
- File: `robstattm/RobStatTM-master/R/WBYlogreg.R` line 41.
- Initial: `robustbase::covMcd` (line 87).

## 4. Inputs / Outputs / Return structure
**Signature:** `WBYlogreg(x0, y, intercept=1, const=0.5, kmax=1000, maxhalf=10)`

Returns the same shape as `BYlogreg`: `coefficients`, `standard.errors`, `fitted.values`, `convergence`, `iter`.

## 5. Dependencies
- RobStatTM
- robustbase

## 6. Python wrapper design
Identical signature to `BYlogreg`:

```python
def wby_logreg(
    X: ArrayLike, y: ArrayLike, *,
    intercept: bool = True, const: float = 0.5,
    kmax: int = 1000, maxhalf: int = 10,
) -> LogregResult: ...
```

Returns the same `LogregResult` dataclass as `by_logreg` — single source of truth for all three logistic wrappers.

## 7. Validation strategy
Same as `BYlogreg.md §7`. Cross-check that `wby_logreg` and `by_logreg` give **different** coefficients on contaminated leverage data (sanity that the weighting is actually doing something).
