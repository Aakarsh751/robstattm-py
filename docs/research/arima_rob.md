# arima_rob (external R package `robustarima` — RESEARCH, Phase 0 2026-06-21)

> **Status:** introspected against the *installed* `robustarima` **0.2.7** (binary,
> built under R 4.5.3). Proposed wrapper `rpm.arima_rob` → `robustarima::arima.rob`.
> Optional stretch package per D-018 / D-024. Unblocks the 6 Chapter-8
> time-series example scripts (resex, ar3, identAR2, identMA1, MA1-AO, ar1).

## 1. Statistical purpose
**Robust ARIMA estimation** via the *filtered tau-estimate* (Bianco, García Ben,
Martínez, Yohai). Fits a regression-ARIMA model that is resistant to additive
outliers (AO) and produces a robustly "cleaned" series. Maronna et al. (2019),
Chapter 8. Supports automatic AR-order identification (`auto.ar=TRUE`).

## 2. R implementation
- **External CRAN package** `robustarima` (0.2.7). Not in this repo, not vendored.
- Exports: `arima.rob`, `arima.rob.fit`, plus three example datasets
  (`frip.dat`, `import.dat`, `newtaxes.dat`) and an `outliers` object.
- Primary entry point:
  ```r
  arima.rob(formula, data, contrasts = NULL, start = NULL, end = NULL,
            p = 0, q = 0, d = 0, sd = 0, freq = 1, sfreq = NULL, sma = FALSE,
            max.p = NULL, auto.ar = FALSE, n.predict = 20, tol = 1e-6,
            max.fcal = 2000, iter = FALSE, innov.outlier = FALSE,
            critv = NULL, ...)
  ```
- There is **no** separate `arima.rob.control` function — all tuning is passed as
  named args to `arima.rob` directly.

## 3. Determinism
`arima.rob` is **deterministic** given its input series. The randomness in the
Ch-8 scripts lives *upstream* in `arima.sim` / `rnorm` (seeded with `set.seed`),
not in the fit. So strict-tier parity needs only a fixed input vector
(`resex` dataset, or a `set_seed`-seeded simulated series reproduced in R).
`auto.ar=TRUE` may emit a non-convergence **warning** (`increase max.fcal`) — this
is expected, does not error, and does not change the returned numbers.

## 4. Return structure (`class "arima.rob"`, 27 components)
Verified by `str(fit)` on `arima.rob(resex ~ 1, p=2, sd=1, sfreq=12)`:

| R component        | shape / type        | notes |
|--------------------|---------------------|-------|
| `regcoef`          | named num (n_reg)   | regression coefficients (e.g. `(Intercept)`) |
| `regcoef.cov`      | num (n_reg,n_reg)   | covariance of `regcoef` |
| `model`            | list(5)             | `$d,$sd,$sfreq,$freq` scalars + `$ar` and/or `$ma` named vecs |
| `model$ar`         | named num (p)       | AR coefficients `AR(1)..AR(p)` (absent if p=0) |
| `model$ma`         | named num (q)       | MA coefficients `MA(1)..MA(q)` (absent if q=0) |
| `sigma.innov`      | num scalar          | innovations scale |
| `sigma.regresid`   | num scalar          | regression-residual scale |
| `sigma.first`      | num scalar          | first-stage scale |
| `innov`            | num (n)             | innovations (leading NAs for the AR warm-up) |
| `innov.acf`        | num (n-...)         | innovations ACF |
| `regresid`         | num (n+n.predict)   | regression residuals |
| `regresid.acf`     | num                 | regression-residual ACF |
| `y`                | named num (n)       | response actually used |
| `y.robust`         | num (n)             | robustly cleaned series (the AO-filtered y) |
| `y.cleaned`        | named num (n)       | cleaned series |
| `x`                | num (n, n_reg)      | design matrix |
| `predict.scales`   | num                 | prediction scales |
| `predict.error`    | num                 | prediction errors |
| `n.predict`        | int                 | # of forecasts requested |
| `tuning.c`,`tauef`,`inf`,`n0` | num scalars | tau tuning / efficiency / influence / n0 |
| `outliers`         | list(8), class `outliers` | detected AO/IO summary |
| `innov.outlier`    | logical             | whether innovation-outlier detection ran |
| `terms`,`assign`,`rank`,`call` | model bookkeeping | |

Script-relevant outputs:
- **resex.R**: `model$ar` (2), `regcoef` (mean), `innov` tail (sorted abs), `y.robust`.
- **ar3.R**: `model$ar` (3), `regcoef` (rescaled by `1-sum(ar)` in-script).
- **MA1-AO.R**: `model$ma` (1), `y.robust`.
- **identAR2.R / identMA1.R**: `auto.ar=TRUE` → selected `model$ar` (order chosen
  by the algorithm), `y.robust` (used for ACF/PACF of the filtered series).
- **ar1.R**: simulation/plotting only — *loads* `robustarima` but never calls
  `arima.rob`. Reproduced as a pure-simulation notebook section (no wrapper call).

## 5. Python wrapper design

```python
@dataclass(frozen=True, slots=True)
class ArimaRobResult:
    ar:            np.ndarray            # model$ar  (empty if none)
    ma:            np.ndarray            # model$ma  (empty if none)
    ar_names:      tuple[str, ...]
    ma_names:      tuple[str, ...]
    regcoef:       np.ndarray            # regression coefficients
    regcoef_names: tuple[str, ...]
    regcoef_cov:   np.ndarray            # (n_reg, n_reg)
    innov:         np.ndarray            # innovations (with leading NaN)
    y_robust:      np.ndarray            # cleaned series
    y_cleaned:     np.ndarray
    regresid:      np.ndarray
    sigma_innov:   float
    sigma_regresid: float
    sigma_first:   float
    d: int; sd: int; sfreq: int; freq: int
    tuning_c: float; tauef: float
    n_predict: int
    innov_outlier: bool
    _r_fit: Any  # raw rpy2 object (repr/compare excluded)
```

```python
def arima_rob(
    formula=None, data=None, *,
    y=None,                 # convenience: a bare numeric vector (resex-style ~1 model)
    p=0, q=0, d=0, sd=0,
    freq=1, sfreq=None, sma=False,
    max_p=None, auto_ar=False,
    n_predict=20, tol=1e-6, max_fcal=2000,
    iter=False, innov_outlier=False, critv=None,
) -> ArimaRobResult: ...
```

**Fit-in-R-space** (D-018 pattern): push the response vector (and any regressors)
to `globalenv`, build the formula in R, run `arima.rob(...)`, extract fields with
`rx2`. `model$ar`/`model$ma` read defensively (either may be absent). The raw fit
is fetched under `default_converter` for `.to_r()` round-trips.

`compat_r` alias: `arima.rob` → `arima_rob`.

## 6. Validation strategy (`tests/external/test_arima_rob.py`, `@needs_robustarima`)
Strict tier (atol=0, rtol=0) vs direct R:
- resex fit (`p=2, sd=1, sfreq=12`): `ar`, `regcoef`, `sigma_innov`, `innov` tail,
  `y_robust`.
- ar3 simulated fit (`set_seed(600)` → reproduce `arima.sim` in R, `p=3`): `ar`.
- MA1-AO simulated fit (`set_seed(200)`, `q=1`): `ma`, `y_robust`.
- auto-AR path (identAR2, `set_seed(700)`, `auto.ar=TRUE`): selected `ar` length +
  values (assert R-equal; tolerate the documented non-convergence warning).

## 7. Dependencies
`robustarima` (0.2.7). Transitive: `splusTimeSeries`, `splusTimeDate`. All install
as Windows binaries (no Rtools needed). Optional — `check_setup()` reports it; tests
skip when absent.
