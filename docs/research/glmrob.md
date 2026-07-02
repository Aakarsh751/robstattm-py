# glmrob (external R package `robustbase` — RESEARCH, Phase 0 2026-06-21)

> **Status:** introspected against the *installed* `robustbase` **0.99-7** (already a
> RobStatTM dependency — present in CORE). Proposed wrapper `rpm.glmrob` →
> `robustbase::glmrob`. Optional-but-usually-present per D-024. Unblocks the robust
> GLM estimators in `epilepsy.R` (Example 7.3, Breslow data): RQL (Mqle) + MT.

## 1. Statistical purpose
**Robust generalized linear models.** `glmrob` fits GLMs (binomial, poisson)
resistant to outliers via several methods. The epilepsy example fits a Poisson
regression of seizure counts with two robust estimators:
- **RQL / Mqle** (robust quasi-likelihood, the default `method="Mqle"`),
- **MT** (`method="MT"`, transformed Mallows-type).

## 2. R implementation
- **Package** `robustbase` (0.99-7) — already installed (CORE; RobStatTM depends on it).
- Signature:
  ```r
  glmrob(formula, family, data, weights, subset, na.action,
         start = NULL, offset,
         method = c("Mqle", "BY", "WBY", "MT"),
         weights.on.x = c("none", "hat", "robCov", "covMcd"),
         control = NULL, model = TRUE, x = FALSE, y = TRUE,
         contrasts = NULL, trace.lev = 0, ...)
  ```
- Per-method control builders exist (`glmrobMqle.control`, `glmrobMT.control`,
  `glmrobBY.control`) — passed via `control=` or as `...`.
- **Note:** `robustbase::glmrob` ≠ `BYlogreg/WBYlogreg/WMLlogreg`, which RobStatTM
  ships and are *already wrapped* (`rpm.by_logreg`, etc.). `glmrob` is a distinct,
  more general entry point (poisson + binomial, multiple methods). No overlap.

## 3. Determinism
**`method="Mqle"` (RQL) is deterministic** — repeated fits give bit-identical
coefficients; no `set_seed` needed. **`method="MT"` is stochastic** (random
subsamples) **but seed-reproducible** — verified: same-seed diff = 0, no-seed diff
≈ 1.5e-4. So the MT parity test seeds both sides (`set.seed`/`set_seed`)
immediately before the fit. (`weights.on.x="covMcd"` would add randomness too, but
the script uses the default `"none"`.)

## 4. Return structure (`class c("glmrob","glm")`, 28 components)
Verified by `str(fit)` on `glmrob(yy ~ xx1+xx2+xx3+xx4, family=poisson)`:

| R component        | shape           | notes |
|--------------------|-----------------|-------|
| `coefficients`     | named num (p)   | robust coefficients |
| `cov`              | num (p,p)       | coef covariance → `sqrt(diag(cov))` = SEs |
| `residuals`        | named num (n)   | working residuals; `residuals(fit)` = deviance resids |
| `fitted.values`    | named num (n)   | fitted means |
| `linear.predictors`| named num (n)   | η = Xβ |
| `w.r`              | num (n)         | robustness weights (residual) |
| `w.x`              | num (n)         | robustness weights (design) |
| `dispersion`       | num             | dispersion (1 for poisson) |
| `tcc`              | num             | tuning constant c |
| `iter`             | int             | iterations |
| `converged`        | logical         | |
| `method`           | chr             | "Mqle" / "MT" |
| `family`           | family object   | |
| `matM`,`matQ`      | num (p,p)       | sandwich pieces |
| `ni`,`y`,`prior.weights`,`model`,`call`,`formula`,`terms`,`data`,`offset`,`control`,`contrasts`,`xlevels` | bookkeeping | |

Script-relevant: `coefficients`, `sqrt(diag(cov))` (SE), `residuals(fit)` (RQL
deviance resids), `fitted` (MT deviance resids computed in-script).

## 5. Python wrapper design

```python
@dataclass(frozen=True, slots=True)
class GlmrobResult:
    coefficients: np.ndarray
    coef_names:   tuple[str, ...]
    cov:          np.ndarray            # (p, p)
    std_errors:   np.ndarray            # sqrt(diag(cov)) convenience
    residuals:    np.ndarray            # residuals(fit) — deviance residuals
    fitted_values: np.ndarray
    linear_predictors: np.ndarray
    weights_r:    np.ndarray            # w.r
    weights_x:    np.ndarray            # w.x
    dispersion:   float
    tcc:          float
    iter:         int
    converged:    bool
    method:       str
    family:       str
    _r_fit:       Any

def glmrob(
    formula, data, *,
    family="poisson",
    method=None,            # None -> "Mqle" (R default); or "MT","BY","WBY"
    weights_on_x="none",
    **control_kwargs,
) -> GlmrobResult: ...
```

**Implementation plan (fit-in-R-space, D-018):** push the DataFrame to `globalenv`,
build the formula + `family=poisson()`/`binomial()` in R, fit `glmrob(...)`, extract
`coefficients/cov/fitted/linear.predictors/w.r/w.x` with `rx2` and `residuals(fit)`
via the R generic (deviance residuals). `compat_r` alias: `glmrob`.

## 6. Validation strategy (`tests/external/test_glmrob.py`, `@needs_glmrob`)
Strict tier vs direct R on the breslow epilepsy design:
- RQL fit (`family=poisson`, default method): `coefficients`, `sqrt(diag(cov))`,
  `residuals`.
- MT fit (`method="MT"`): `coefficients`, `sqrt(diag(cov))`.
Data via `rpm.datasets.breslow_dat()`. `robustbase` is in CORE so this test runs in
normal CI.

## 7. Dependencies
`robustbase` (already CORE). No extra install. The ML `glm()` baseline in
`epilepsy.R` is a **comparator only** — reproduced via R `glm()` in the notebook,
not exposed as a new Python wrapper (D-024 non-goal).
