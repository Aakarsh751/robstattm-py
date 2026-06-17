# BYlogreg (alias logregBY)

## 1. Statistical purpose
**Bianco–Yohai M-estimator for logistic regression**. Maronna et al. (2019, §7.2). First-generation robust logistic regression; superseded in the book's primary recommendation by `WBYlogreg` (weighted, redescending).

## 2. Mathematical background
M-estimator using the BY ρ-function; downweights observations with extreme linear predictor under the model.

## 3. R implementation
- File: `robstattm/RobStatTM-master/R/BYlogreg.R` line 40.
- Initial: `robustbase::covMcd` (line 86) for an MCD covariance used in centering.

## 4. Inputs / Outputs / Return structure
**Signature:** `BYlogreg(x0, y, intercept=1, const=0.5, kmax=1000, maxhalf=10)`

Returns list with `coefficients`, `standard.errors`, `convergence`, `iter`, `fitted.values`.

## 5. Dependencies
- RobStatTM
- robustbase

## 6. Python wrapper design

```python
def by_logreg(
    X: ArrayLike,                # (n, p)
    y: ArrayLike,                # (n,) {0, 1}
    *,
    intercept: bool = True,
    const: float = 0.5,
    kmax: int = 1000,
    maxhalf: int = 10,
) -> LogregResult: ...
```

```python
@dataclass(frozen=True, slots=True)
class LogregResult:
    coefficients: np.ndarray
    standard_errors: np.ndarray  # R: standard.errors
    fitted_values: np.ndarray    # probabilities
    converged: bool
    iter: int
```

## 7. Validation strategy
Cases 1, 2, 7, 10 + GLM case 15 (probabilities in [0,1]) + 16 (convergence flag matches). Reproduce a Maronna §7.2 example (e.g. `skin.R` from `examples-scripts/`).
