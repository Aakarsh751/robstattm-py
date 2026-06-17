# lmrobdetMM  **(critical / flagship wrapper)**

## 1. Statistical purpose
MM-estimator for linear regression with **optimal $\rho$** family (Yohai 1987; Maronna et al. 2019, §5.3, §5.9). The primary recommendation for general-purpose robust regression in the book. High breakdown (S-initialization) followed by efficiency boost (M-refinement).

## 2. Mathematical background
Two-stage:
1. **S step** — robust regression via the S-estimator with bisquare or m-opt $\rho$; achieves 50% breakdown via the FastS algorithm.
2. **M step** — IRLS refinement with a re-descending $\psi$ tuned to a target asymptotic efficiency (default 0.95).
Initial estimate from `pyinit::pyinit` (Peña–Yohai) when `initial="pyinit"` (default for moderate $p$).

## 3. R implementation
- File: `robstattm/RobStatTM-master/R/lmrobdet.R` line 97.
- Internal MM solver: `lmrob.MM` (file `lmrob.MM.R`); a long file containing IRLS, τ-correction (`tcorr`), and standard-error machinery.
- Helpers: `refine.sm` (line 720), `our.solve` (line 799).
- Calls `pyinit::pyinit` for initial estimate; `robustbase::lmrob` for τ-correction; `robustbase::robMD` for leverage.

## 4. Inputs / Outputs / Return structure
**Signature:** `lmrobdetMM(formula, data, subset, weights, na.action, family="mopt", control=lmrobdet.control(...))`

Returns S3 list of class `"lmrobdetMM"`. Key fields (subject to confirmation via `str(fit)` at implementation time):
`coefficients`, `scale`, `residuals`, `fitted.values`, `rweights`, `weights`, `rank`, `df.residual`, `cov`, `qr`, `iter`, `converged`, `r.squared` (robust $R^2$ from `INVTR2.R`), `MD`, `control`, `call`, `terms`, `model`, `xlevels`, `assign`.

## 5. Dependencies
- RobStatTM
- pyinit (when `initial="pyinit"`, default)
- robustbase (covMcd, lmrob, robMD)

## 6. Python wrapper design

```python
def lmrobdet_mm(
    formula: FormulaLike,
    data: pd.DataFrame,
    *,
    control: LmrobdetControl | None = None,
    family: Literal["mopt","bisquare","huber"] = "mopt",
    efficiency: float = 0.95,
    weights: ArrayLike | None = None,
    subset: ArrayLike | None = None,
    na_action: Literal["omit","fail","pass"] = "omit",
) -> LmrobdetMMResult: ...
```

Convenience: when `control is None`, build it from `family` / `efficiency` kwargs; mutually exclusive with passing `control`.

```python
@dataclass(frozen=True, slots=True)
class LmrobdetMMResult:
    coefficients: np.ndarray
    coef_names: tuple[str, ...]
    scale: float
    residuals: np.ndarray
    fitted_values: np.ndarray
    rweights: np.ndarray
    weights: np.ndarray
    rank: int
    df_residual: int
    cov: np.ndarray
    iter: int
    converged: bool
    r_squared: float
    md: np.ndarray | None
    control: LmrobdetControl
```

Plus a `summary()` method returning a printable table mirroring `summary.lmrobdetMM` (line 539 of `lmrobdet.R`).

**Edge cases:** singular X; perfect fit; missing data per `na_action`; categorical columns (convert via patsy / pandas2ri).

## 7. Validation strategy
All 11 wrapper test cases from `docs/validation_strategy.md §3`, plus golden `mineral.R` reproduction (Figs 5.1–5.7). Strict-tier on every numeric field. Plotting helper `robstatm_py.plotting.residuals(fit)` validated via pytest-mpl.
