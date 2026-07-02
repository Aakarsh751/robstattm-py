# cubinf (external R package `robcbi` — RESEARCH, Phase 0 2026-06-21)

> **Status:** introspected from the **CRAN-archived source tarball** `robcbi_1.1-4`
> (2023-08-21). **Not installed on this machine** — see §3 build blocker.
> Proposed wrapper `rpm.cubinf` → `robcbi::cubinf` (+ `rpm.cubinf_control`).
> Optional stretch package per D-018 / D-024. Unblocks the **CUBIF** estimator in
> `epilepsy.R` (Example 7.3).

## 1. Statistical purpose
**CUBIF** = Conditionally Unbiased Bounded-Influence estimates for discrete GLMs
(Künsch, Stefanski & Carroll 1989) in three cases: Bernoulli, Binomial, Poisson.
The epilepsy example uses it for the Poisson seizure-count model.

## 2. R implementation
- **External CRAN package** `robcbi` (1.1-4) — **archived** (removed from the main
  CRAN index; available under `.../src/contrib/Archive/robcbi/`). `NeedsCompilation:
  no` (pure R) **but** `Imports: robeth`.
- Signatures (from source `R/cubinfAM.R`):
  ```r
  cubinf(x, y, weights = NULL, start = NULL, etastart = NULL, mustart = NULL,
         offset = NULL, family = binomial(), control = cubinf.control(...),
         intercept = FALSE, ...)

  cubinf.control(tlo = 0.001, tua = 1e-06, mxx = 30, mxt = 10, mxf = 10,
                 ntm = 0, gma = 1, iug = 1, ipo = 1, ilg = 2, icn = 1,
                 icv = 1, ufact = 0, cpar = 1.5, null.dev = TRUE, ...)
  ```
- `x` is a **design matrix** (variables in columns), `y` a response vector. With
  `intercept=FALSE` (the default) the caller supplies the intercept column —
  exactly what `epilepsy.R` does (`XX <- cbind(rep(1,59), ...)`).
- Numerical engine: ROBETH Fortran subroutines (`GINTAC`, `GYMAIN`, `GYTSTP`,
  `GYCSTP`, `GYASTP`) via the `robeth` package.

## 3. Build blocker (must surface to user)
`robcbi` is pure R, but its dependency **`robeth` is a Fortran package with NO R-4.5
Windows binary** on CRAN → it must be **compiled from source, which requires
Rtools45** (not installed on this machine). Consequently `cubinf` **cannot be fitted
or strict-tier-validated here** until either Rtools45 is installed (then
`install.packages("robeth"); install.packages(<robcbi archive tarball>)`) or the
user installs `robcbi`+`robeth` themselves.

Two ways forward (user decides — see D-024 proposal):
- **(A)** Install Rtools45 → compile `robeth` + `robcbi` → implement `cubinf` and run
  its strict-tier test like the other three packages. (~1 large download.)
- **(B)** Ship the `rpm.cubinf` wrapper coded to the verified source signature/return
  but **skip-tested** (`@needs_robcbi` skips when absent — identical to how
  `pense`/`GSE` tests skip when their packages are missing). The epilepsy notebook's
  CUBIF section then runs only on machines with `robcbi` installed; its numbers are
  documented as book Table 7.3 values otherwise (alongside the already-documented
  MATLAB `epiMP` constants).

## 4. `epilepsy.R` call shape
```r
ctrl <- robcbi::cubinf.control(ufact = 1.1)
epiCUBIF <- robcbi::cubinf(XX, yy, family = poisson(), null.dev = FALSE, control = ctrl)
# XX: 59x5 design with explicit intercept col; yy: counts
epiCUBIF$coefficients
sqrt(diag(epiCUBIF$cov))
# deviance residuals computed in-script from yy & epiCUBIF$fitted
```
Note `null.dev=FALSE` is passed as a top-level `...` arg (folded into control).

## 5. Return structure (`class "cubinf"`, from `man/cubinf.Rd` + `R/cubinfAM.R`)

| R component        | notes |
|--------------------|-------|
| `coefficients`     | coefficient estimates |
| `cov`              | estimated coef covariance → `sqrt(diag(cov))` = SE |
| `fitted.values`    | fitted means (used for deviance resids in-script) |
| `residuals`        | working residuals |
| `rsdev`            | deviance residuals |
| `linear.predictors`| η = Xβ |
| `ci`               | final bias corrections |
| `A`                | final A matrix |
| `ai`               | a_i = ufact/|A x_i| |
| `rank`,`df.residual` | model dims |
| `converged`        | logical (FALSE if max iters hit) |
| `iter`             | iterations |
| `gradient`,`inv.hessian` | final optimizer state |
| `family`           | with `ics` ∈ {1 Bernoulli, 2 Binomial, 3 Poisson} |
| `control`,`prior.weights`,`y` | bookkeeping |

## 6. Python wrapper design

```python
@dataclass(frozen=True, slots=True)
class CubinfResult:
    coefficients: np.ndarray
    coef_names:   tuple[str, ...]
    cov:          np.ndarray
    std_errors:   np.ndarray            # sqrt(diag(cov))
    fitted_values: np.ndarray
    residuals:    np.ndarray            # working residuals
    deviance_residuals: np.ndarray      # rsdev
    linear_predictors: np.ndarray
    rank:         int
    df_residual:  float
    converged:    bool
    iter:         int
    family:       str
    _r_fit:       Any

def cubinf(
    X, y, *,
    family="poisson",
    intercept=False,
    null_dev=True,
    ufact=0.0,
    **control_kwargs,
) -> CubinfResult: ...
```

**Implementation plan (fit-in-R-space, D-018):** push `X`/`y` to `globalenv`, build
`family=poisson()`, build the control via `cubinf.control(ufact=..., null.dev=...)`,
fit `robcbi::cubinf(...)`, extract fields with `rx2`. `compat_r` alias `cubinf`.

## 7. Validation strategy (`tests/external/test_cubinf.py`, `@needs_robcbi`)
Strict tier vs direct R on the epilepsy `XX`/`yy` design (`ufact=1.1`,
`null.dev=FALSE`, `family=poisson`): `coefficients`, `sqrt(diag(cov))`,
deviance residuals. **Only runs where `robcbi`+`robeth` are installed** (§3);
auto-skips otherwise.

## 8. Dependencies
`robcbi` (1.1-4, archived) + `robeth` (Fortran, **needs Rtools45 on Windows**).
Both user-installed, never vendored (D-003).
