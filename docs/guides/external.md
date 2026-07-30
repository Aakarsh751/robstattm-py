# External (stretch) estimators

A handful of robust estimators referenced by the textbook ship in **separate
CRAN packages** rather than in RobStatTM itself. RobStatTM-Py wraps them under
`robstattm_py.external` (and re-exports them at the top level), with the same
rpy2 bridge and bit-for-bit parity as the core wrappers.

These require their R package to be installed separately:

```r
install.packages(c("pense", "GSE", "robustarima", "robustvarComp", "WWGbook"))
# robcbi is CRAN-archived and needs its Fortran dependency 'robeth' (Rtools on
# Windows); install both from the CRAN Archive — see the cubinf section below.
# robustbase (for glmrob) is already a RobStatTM dependency.
```

`rpm.check_setup()` reports whether each is available; the wrappers raise a
clear `RobStatTMSetupError` if you call one whose package is missing.

**Maronna et al. proposal stretch (location/scatter & regression):**

| Function | R original | Package | What it does |
|---|---|---|---|
| [`pense`](#pense) | `pense::pense` | `pense` | Robust elastic-net S-estimator — full regularization path. |
| [`pense_cv`](#pense_cv) | `pense::pense_cv` | `pense` | Robust elastic-net with k-fold cross-validation. |
| [`gse`](#gse) | `GSE::GSE` | `GSE` | Generalized S-estimator of location/scatter with **missing data**. |
| [`tsgs`](#tsgs) | `GSE::TSGS` | `GSE` | Two-step GSE for **cell-wise** outliers. |

**Example-script reproduction (D-024) — these unblock the remaining textbook scripts:**

| Function | R original | Package | Script(s) | What it does |
|---|---|---|---|---|
| [`arima_rob`](#arima_rob) | `robustarima::arima.rob` | `robustarima` | resex, ar3, identAR2, identMA1, MA1-AO, ar1 (Ch 8) | Robust ARIMA via the filtered tau-estimate. |
| [`var_comprob`](#var_comprob) | `robustvarComp::varComprob` | `robustvarComp` | autism (Ch 6) | Robust variance-component / mixed models. |
| [`var_comprob_control`](#var_comprob) | `robustvarComp::varComprob.control` | `robustvarComp` | autism | Control object for `var_comprob`. |
| [`glmrob`](#glmrob) | `robustbase::glmrob` | `robustbase` | epilepsy (Ch 7) | Robust GLM (Poisson RQL/Mqle + MT). |
| [`cubinf`](#cubinf) | `robcbi::cubinf` | `robcbi` (+ `robeth`) | epilepsy (Ch 7) | CUBIF bounded-influence GLM. |

> All four are **stochastic** (Peña-Yohai / EMVE initial estimates, and CV folds
> for `pense_cv`). Call `rpm.set_seed(n)` immediately before for reproducible
> results.

## `pense`

Robust elastic-net regression (penalized S-estimator; the `alpha=1` case is the
MM-lasso). Returns the coefficient matrix along the automatically-chosen `lambda`
path, extracted via R's own `coef(fit, lambda=…)` so it matches R exactly.

```python
def pense(X, y, *, alpha=0.5, nlambda=50, bdp=0.25,
          intercept=True, standardize=True) -> PenseResult
```

| Field | Shape | Meaning |
|---|---|---|
| `coefficients` | `(p+1, n_lambda)` | intercept (row 0) + slopes, one column per `lambda` |
| `intercepts` / `slopes` | `(n_lambda,)` / `(p, n_lambda)` | convenience views |
| `lambda_path` | `(n_lambda,)` | penalty levels, descending |
| `alpha`, `bdp` | scalar | mixing parameter and breakdown point actually used |

```python
import numpy as np
import robstattm_py as rpm

rng = np.random.default_rng(0)
X = rng.standard_normal((60, 8))
y = X @ np.array([2.0, 0, -1.5, 0, 0, 0, 1.0, 0]) + rng.standard_normal(60)

rpm.set_seed(1)
fit = rpm.pense(X, y, alpha=0.75, nlambda=25)
print(fit.coefficients.shape)        # (9, 25)  -> intercept + 8 slopes
print(fit.lambda_path[:3])
```

## `pense_cv`

Same model selected by cross-validation; `coef_min` is `coef(fit, lambda="min")`.

```python
def pense_cv(X, y, *, alpha=0.5, nlambda=50, bdp=0.25,
             cv_k=5, cv_repl=1, intercept=True, standardize=True) -> PenseCVResult
```

`coef_min` (`(p+1,)`), `lambda_min`, `cv_avg` / `cv_se` per lambda, and the full
`cvres` table are returned.

```python
rpm.set_seed(1)
cv = rpm.pense_cv(X, y, alpha=0.75, nlambda=25, cv_k=5)
print(cv.lambda_min)
print(cv.coef_min.round(3))
```

## `gse`

Generalized S-estimator of multivariate location and scatter that handles
**missing entries** (`NaN`) natively — the point of the GSE family.

```python
def gse(X, *, tol=1e-4, maxiter=150, method="bisquare") -> GSEResult
```

Returns `mu` (location), `cov` (scatter), `pmd` / `pmd_adj` (partial Mahalanobis
distances), `weights`, `ximp` (imputed data), and scalars `sc` / `iter` / `eps`.

```python
import numpy as np, robstattm_py as rpm

X = rpm.datasets.wine().to_numpy()[:, :5].copy()
X[::10, 0] = np.nan                      # introduce some missingness
rpm.set_seed(7)
g = rpm.gse(X)
print(g.mu.shape, g.cov.shape)           # (5,) (5, 5)
print(np.isfinite(g.ximp).all())         # True — missing cells imputed
```

## `tsgs`

Two-step GSE for **cell-wise** contamination: step 1 flags individual outlying
cells (setting them to `NaN`), step 2 runs GSE on the filtered data. Same fields
as `gse` plus `xf`, the filtered matrix.

```python
def tsgs(X, *, filter="UBF-DDC", partial_impute=False,
         tol=1e-4, maxiter=150, method="bisquare") -> TSGSResult
```

```python
rpm.set_seed(7)
t = rpm.tsgs(rpm.datasets.wine().to_numpy()[:, :5])
print(t.cov.shape)                       # (5, 5)
print(np.isnan(t.xf).any())              # cells the filter flagged are NaN
```

## `arima_rob`

Robust ARIMA estimation via the *filtered tau-estimate* (`robustarima::arima.rob`),
resistant to additive outliers. Reproduces the Chapter-8 time-series scripts.
`arima.rob` is **deterministic** given its input series — no seeding needed (the
example scripts seed `arima.sim` upstream).

```python
def arima_rob(formula=None, data=None, *, y=None,
              p=0, q=0, d=0, sd=0, freq=1, sfreq=None, sma=False,
              max_p=None, auto_ar=False, n_predict=20, tol=1e-6,
              max_fcal=2000, iter=False, innov_outlier=False, critv=None) -> ArimaRobResult
```

Pass either a bare response vector `y=...` (fits `y ~ 1`, as every Ch-8 script does)
or a `formula` + `data`. The model list carries `ar` and/or `ma` depending on
`p`/`q`/`auto_ar`.

| Field | Meaning |
|---|---|
| `ar` / `ma` | AR / MA coefficients (`model$ar` / `model$ma`; empty if none) |
| `regcoef` / `regcoef_cov` | regression coefficients + covariance |
| `innov` | innovations (leading NaN during AR warm-up) |
| `y_robust` / `y_cleaned` | robustly cleaned series |
| `sigma_innov` / `sigma_regresid` / `sigma_first` | scales |

```python
import robstattm_py as rpm

resex = rpm.datasets.resex()["resex"].to_numpy()
fit = rpm.arima_rob(y=resex, p=2, sd=1, sfreq=12)   # resex.R, Example 8.6
print(fit.ar)          # AR(1), AR(2)
print(fit.regcoef)     # mean of the differenced series
```

## `var_comprob`

Robust variance-component / linear-mixed-model estimation
(`robustvarComp::varComprob`). Reproduces the autism growth-model example.
**Stochastic** (default `fixed.init="lmrob.S"`, `cov.init="TSGS"`) — call
`rpm.set_seed(n)` before. A plain `data.frame` is accepted (no `nlme::groupedData`
needed — the `groups` matrix drives the grouping).

```python
def var_comprob_control(*, method=None, psi=None, lower=None, upper=None,
                        cov_init=None, fixed_init=None, epsilon=None, max_it=None,
                        beta_univ=None, gamma_univ=None, cov=None, **extra) -> VarComprobControl

def var_comprob(fixed, data, *, groups, varcov, varcov_names=None,
                control=None) -> VarComprobResult
```

`groups` is an `(n_obs, 2)` integer matrix; `varcov` is the list `K` of `p×p`
covariance kernels. Returns `beta`/`eta`/`gamma` (+ their `vcov_*`), `sigma2`,
`Sigma`, `scales`, `iterations`, `method`.

```python
import numpy as np, robstattm_py as rpm

ctrl = rpm.var_comprob_control(lower=[0.01, 0.01, 0.01, -np.inf, -np.inf, -np.inf])
rpm.set_seed(2468)
fit = rpm.var_comprob(
    "vsae ~ age.2 + I(age.2^2) + sicdegp2.f + age.2:sicdegp2.f + I(age.2^2):sicdegp2.f",
    autism_df, groups=groups, varcov=K, control=ctrl,
)
print(fit.beta)        # fixed effects
print(fit.sigma2)      # error variance
```

## `glmrob`

Robust generalized linear models (`robustbase::glmrob`) for Poisson and binomial
responses. Reproduces the epilepsy RQL/Mqle and MT fits. **`method="Mqle"` (RQL)
is deterministic; `method="MT"` is stochastic but seed-reproducible** — seed before
an MT fit.

```python
def glmrob(formula, data, *, family="poisson", method=None,
           weights_on_x="none", **control_kwargs) -> GlmrobResult
```

Returns `coefficients` (+ `coef_names`), `cov`, `std_errors` (`sqrt(diag(cov))`),
`residuals` (deviance residuals for Mqle), `fitted_values`, robustness weights,
`iter`, `converged`, `method`.

```python
import robstattm_py as rpm

epi = rpm.datasets.breslow_dat()                            # cols: sumY, Age10, Base4, Trt
df = epi.assign(prog=(epi["Trt"] == "progabide"))
df = df.assign(interac=df["Base4"] * df["prog"])            # Base4 x Progabide
formula = "sumY ~ Age10 + Base4 + prog + interac"
rql = rpm.glmrob(formula, df, family="poisson")             # epilepsy.R RQL
print(rql.coefficients, rql.std_errors)
rpm.set_seed(11)                                            # MT is stochastic
mt = rpm.glmrob(formula, df, family="poisson", method="MT")
```

## `cubinf`

CUBIF — Conditionally Unbiased Bounded-Influence GLM estimates (`robcbi::cubinf`,
Künsch et al. 1989). Reproduces the epilepsy CUBIF fit. **Deterministic.**

> **Install:** `robcbi` is CRAN-archived and imports the Fortran package `robeth`
> (also archived, no Windows binary). On Windows install **Rtools**, then from the
> CRAN Archive:
> ```r
> install.packages("https://cran.r-project.org/src/contrib/Archive/robeth/robeth_2.7-8.tar.gz", repos=NULL, type="source")
> install.packages("https://cran.r-project.org/src/contrib/Archive/robcbi/robcbi_1.1-4.tar.gz", repos=NULL, type="source")
> ```

```python
def cubinf(X, y, *, family="poisson", intercept=False,
           null_dev=True, ufact=0.0, **control_kwargs) -> CubinfResult
```

`X` is a **design matrix** (variables in columns); supply your own intercept column
when `intercept=False` (the default), as `epilepsy.R` does. Returns `coefficients`,
`cov`, `std_errors`, `fitted_values`, `deviance_residuals` (`rsdev`), `converged`.

```python
import numpy as np, robstattm_py as rpm

XX = np.column_stack([np.ones(59), age10, base4, progabide, base4*progabide])
fit = rpm.cubinf(XX, yy, family="poisson", intercept=False, null_dev=False, ufact=1.1)
print(fit.coefficients, fit.std_errors)
```

## See also

- [API reference](../api/index.md) — the core (non-external) wrappers.
- [Setup & utilities](utilities.md) — `check_setup()` reports external-package availability.
