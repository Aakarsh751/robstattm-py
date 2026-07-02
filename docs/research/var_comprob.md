# var_comprob (external R package `robustvarComp` — RESEARCH, Phase 0 2026-06-21)

> **Status:** introspected against the *installed* `robustvarComp` **0.1-7** (binary,
> built under R 4.5.3). Proposed wrappers `rpm.var_comprob` →
> `robustvarComp::varComprob` and `rpm.var_comprob_control` →
> `robustvarComp::varComprob.control`. Optional stretch package per D-018 / D-024.
> Unblocks `autism.R` (Example 6.7, Tables 6.8–6.9).

## 1. Statistical purpose
**Robust estimation of variance-component / linear-mixed models** via composite
robust S/Tau/MM estimators built on robust pairwise (composite) likelihood.
Maronna et al. (2019), §6.x. The autism example fits a random-effects growth model
to repeated `vsae` measurements across `childid` groups.

## 2. R implementation
- **External CRAN package** `robustvarComp` (0.1-7). Imports `robustbase`, `GSE`,
  `nlme`, `numDeriv`, `Matrix`. Installs as a Windows binary (no Rtools needed).
- Exports (only 3): `varComprob`, `varComprob.control`, `summary.varComprob`.
- Signatures:
  ```r
  varComprob(fixed, data, random, groups, varcov, weights, subset,
             family = gaussian("identity"), na.action, offset,
             control = varComprob.control(...), doFit = TRUE,
             normalizeTrace = FALSE, contrasts = NULL,
             model = TRUE, X = TRUE, Y = TRUE, K = TRUE, ...)

  varComprob.control(init = NULL, lower = 0, upper = Inf, epsilon = 0.001,
             tuning.chi = NULL, bb = 0.5, tuning.psi = NULL, arp.chi = 0.1,
             arp.psi = NULL, max.it = 100, rel.tol.beta = 1e-6,
             rel.tol.gamma = 1e-5, rel.tol.scale = 1e-5, trace.lev = 0,
             method = c("compositeTau","compositeS","compositeMM","Tau","S","MM"),
             psi = c("optimal","bisquare","rocke"),
             beta.univ = FALSE, gamma.univ = FALSE,
             fixed.init = c("lmrob.S","lmRob"),
             cov.init = c("TSGS","2SGS","covOGK"), cov = TRUE, ...)
  ```

## 3. The `autism.R` call shape (what the wrapper must support)
- `fixed`: a formula `vsae ~ age.2 + I(age.2^2) + sicdegp2.f + age.2:sicdegp2.f + I(age.2^2):sicdegp2.f`
- `groups`: integer matrix `cbind(rep(1:p, each=n), rep(1:n, p))`, shape `(p*n, 2)` =
  `(205, 2)` here (p=5 time points, n=41 subjects). Column 1 = within-group index,
  column 2 = group id.
- `varcov`: a **named list `K` of 6** `p×p` covariance kernels built from
  `tcrossprod` of basis vectors `z1=1, z2=(0,1,3,7,11), z3=z2^2`.
- `data`: an **`nlme::groupedData`** object (`vsae ~ age.2 | childid`). Must be
  rebuilt in R from the prepared DataFrame.
- Two fits:
  1. **Composite Tau** (default `method`): `control=varComprob.control(lower=c(0.01,0.01,0.01,-Inf,-Inf,-Inf))`.
  2. **Classic S**: `control=varComprob.control(method="S", psi="rocke", cov.init="covOGK", lower=...)`.

## 4. Determinism
**Stochastic.** Default `fixed.init="lmrob.S"` (random subsampling) and
`cov.init="TSGS"` (EMVE random start) both draw randomness. → strict-tier parity
requires `set_seed(...)` immediately before each fit, with the *same* seed used by
the R reference. The Classic-S fit uses `cov.init="covOGK"` (deterministic) but
still has the stochastic `lmrob.S` init → seed still required.

## 5. Return structure (`class c("varComprob.compositeTau","varComprob.fit","varComprob")`, 32 components)
Verified by `str(fit)` on the Composite-Tau autism fit:

| R component  | shape                  | notes |
|--------------|------------------------|-------|
| `beta`       | named num (n_fixef=9)  | fixed-effect coefficients |
| `vcov.beta`  | num (9,9)              | covariance of `beta` |
| `eta`        | named num (6)          | variance-component params (one per K kernel) |
| `vcov.eta`   | num (6,6)              | |
| `gamma`      | named num (6)          | reparameterised variance comps |
| `vcov.gamma` | num (6,6)              | |
| `eta0`       | named num              | error variance (raw) |
| `sigma2`     | named num              | `error variance` (final) |
| `resid`      | num (p, n)             | residual matrix |
| `weights`/`weights.1`/`weights.2`/`dotweights` | num (p*(p+1)/2, n) | robust weights |
| `Sigma`      | num (p,p)              | estimated group covariance |
| `scales`     | num (p*(p+1)/2)        | composite scales |
| `min`,`tau`,`scale0` | num scalars    | objective / tau / initial scale |
| `iterations` | num                    | iteration count |
| `initial.values` | list(4)            | starting values |
| `control`    | list(21)               | the control actually used |
| `fixef`      | = `beta`               | alias |
| `parms`      | = `gamma`              | alias |
| `nobs`,`na.action`,`terms`,`model`,`X`,`Y`,`K`,`random.labels`,`call` | bookkeeping | |

`summary(fit)` builds the coefficient table the script prints (beta + SE + t).

## 6. Python wrapper design

```python
@dataclass(frozen=True, slots=True)
class VarComprobResult:
    beta:         np.ndarray            # fixed effects
    beta_names:   tuple[str, ...]
    vcov_beta:    np.ndarray
    eta:          np.ndarray            # variance components
    eta_names:    tuple[str, ...]
    vcov_eta:     np.ndarray
    gamma:        np.ndarray
    vcov_gamma:   np.ndarray
    sigma2:       float                 # error variance
    Sigma:        np.ndarray            # (p, p) group covariance
    scales:       np.ndarray
    min:          float
    iterations:   int
    method:       str                   # "compositeTau" / "S" / ...
    _r_fit:       Any
    # convenience: .summary() -> pandas table from summary.varComprob

# control is a thin dict-like passthrough (validated against R defaults)
def var_comprob_control(
    *, method="compositeTau", psi="optimal",
    lower=0.0, upper=float("inf"), epsilon=1e-3,
    cov_init="TSGS", fixed_init="lmrob.S",
    max_it=100, **kwargs,
) -> VarComprobControl: ...

def var_comprob(
    fixed, data, *, groups, varcov,
    control=None, family="gaussian", ...,
) -> VarComprobResult: ...
```

**Implementation plan (fit-in-R-space, D-018):**
- Build `K` list, `groups` matrix, and the prepared DataFrame in Python; push to
  `globalenv`.
- Reconstruct `groupedData` in R: `nlme::groupedData(vsae ~ age.2 | childid, data=...)`.
- Build the control list in R from `var_comprob_control` args (threaded faithfully —
  same lesson as D-021; the `lower=c(...)` vector and `psi`/`cov.init`/`method` must
  reach R exactly).
- Fit, then extract `beta/eta/gamma/sigma2/Sigma/vcov.*` with `rx2`.
- `set_seed` before the fit for reproducibility (§4).

`compat_r` aliases: `varComprob` → `var_comprob`, `varComprob.control` → `var_comprob_control`.

## 7. Validation strategy (`tests/external/test_var_comprob.py`, `@needs_robustvarcomp` + `@needs_wwgbook`)
Strict tier vs direct R on the canonical autism Composite-Tau fit (build identical
K/groups/groupedData/control in both paths, same `set_seed`): `beta`, `eta`,
`gamma`, `sigma2`, `Sigma`, `vcov.beta` diag. Plus a Classic-S smoke/parity check.
Auto-skips when `robustvarComp` or `WWGbook` absent.

## 8. Dependencies
`robustvarComp` (0.1-7), `nlme` (3.1.168, already present), `WWGbook` (1.0.2, the
`autism` data — note the script's `package='WWGbook'`; the resume prompt's
`WWWGbook` is a typo). All Windows binaries (no Rtools).
