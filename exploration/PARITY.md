# R ↔ Python Parity Reference

**Question:** Have we reproduced *all* R functionalities, arguments, and customisations?

**Answer:** **All exported RobStatTM estimators are wrapped**, and exposed
parameters are tested for numerical equivalence. But the Python API is
**intentionally narrower** than full R `lm()`-style ergonomics in places.

---

## 1. Callable coverage (NAMESPACE)

| Bucket | R exports | Python | Notes |
|--------|-----------|--------|-------|
| Estimators | 42 exposed | 42 wrapped | 4 internal (`DCML`, `cov.dcml`, `MMPY`, `SMPY`) deliberately hidden |
| S3 methods | 8 used in book | 8 as dataclass methods | `drop1.lmrobdetMM` → use `step_lmrobdet` |
| Datasets | 20 | 20 loaders | `rpm.datasets.<name>()` |
| ψ helpers | 9 | 9 in `rpm.psi` | |
| Stretch | `pense`, `GSE`, `TSGS` | `rpm.pense`, `gse`, `tsgs` | Optional CRAN deps |

Authoritative matrix: `docs/coverage_matrix.md`.

---

## 2. Argument parity by wrapper

### Regression (`lmrobdet_mm`, `lmrobdet_dcml`, `lmrob_m`)

| R argument | Python | Status |
|------------|--------|--------|
| `formula`, `data` | ✓ | Formula + DataFrame; also `X`/`y` matrix API |
| `control` | ✓ | Full 25-field `LmrobdetControl` / `lmrobdet_control()` |
| `family`, `efficiency` | ✓ | Shortcuts when `control=None` |
| `subset` | ✗ | Filter DataFrame in Python before calling |
| `weights` | ✗ | Not exposed |
| `na.action` | ✗ | Drop NAs in pandas first |

**Control object (`lmrobdet.control`)** — all 25 R keys mapped to Python
snake_case (`max_it`, `refine_s_py`, `mscale_rho_fun`, …). See
`src/robstattm_py/regression/control.py`.

### Univariate (`loc_scale_m`, `m_scale`)

| R argument | Python | Status |
|------------|--------|--------|
| `psi` / family | ✓ | 6 families |
| `eff` / efficiency | ✓ | |
| `maxit`, `tol` | ✓ | |
| `na.rm` | ✓ | as `na_rm` |

### Covariance (`cov_rob_mm`, `cov_rob_rocke`, `cov_rob`, `fastmve`)

| R argument | Python | Status |
|------------|--------|--------|
| `maxit`, `tolpar`, `corr` | ✓ | on MM/Rocke |
| `type` (`auto`/`MM`/`Rocke`) | ✓ | on `cov_rob` dispatcher |
| `eff`, `maxit` (Rocke-specific) | ✓ | on `cov_rob_rocke` |

### PCA (`pca_rob_s`, `prcomp_rob`)

| R argument | Python | Status |
|------------|--------|--------|
| `k`, `method`, `scale` | ✓ | See wrapper docstrings |
| `scores` | ✓ | on `prcomp_rob` |

### GLM (`by_logreg`, `wby_logreg`, `wml_logreg`)

| R argument | Python | Status |
|------------|--------|--------|
| `X`, `y`, `intercept` | ✓ | Matrix API (no formula) |
| `const`, `kmax`, `maxhalf` | ✓ | BY / WBY |
| Internal `x0` init | ✗ | Handled inside R |

### Not in `docs/examples/` but wrapped

- `step_lmrobdet`, `rob_linear_test`, `invtr2`, `refine_sm`
- `lmrobdet_dcml`, `lmrob_m`
- `cov_classic`, `cov_rob`, `fastmve`, `kurt_sd_new`
- `pca_rob_s` (lower-level vs `prcomp_rob`)
- `rpm.datasets.load("robustbase", "coleman")` cross-package loader

---

## 3. Return-value parity

Python dataclasses expose the **numeric fields users need for analysis**.
Some R-only bookkeeping is omitted:

| R field | Python | Workaround |
|---------|--------|------------|
| `qr`, `terms`, `assign`, `xlevels` | omitted | `fit._r_fit` or `fit.to_r()` |
| `MD` (Mahalanobis distances in regression) | omitted | recompute from residuals or use R object |
| `weights` (case weights) | omitted | use `rweights` (robust weights) |
| `init` (full S-fit object) | partial | `scale_s`, `iters_const` exposed |

For strict field-by-field checks on **exposed** attributes, see `tests/`.

---

## 4. Customisation examples *not* in `docs/examples/`

These are exercised in `exploration/`:

```python
import robstattm_py as rpm

rpm.set_seed(42)

# Bisquare family at 85% efficiency (book default in many scripts)
ctrl = rpm.lmrobdet_control(bb=0.5, efficiency=0.85, family="bisquare")
fit = rpm.lmrobdet_mm("time ~ n.shocks", data=rpm.datasets.shock(), control=ctrl)

# M-estimator regression (lighter than MM)
fit_m = rpm.lmrob_m("response1 ~ variety + block", data=rpm.datasets.oats(), control=ctrl)

# DCML regression (distance-constrained MLE)
fit_dcml = rpm.lmrobdet_dcml("zinc ~ copper", data=rpm.datasets.mineral())

# Stepwise RFPE selection
full = rpm.lmrobdet_mm("stack.loss ~ Air.Flow + Water.Temp + Acid.Conc.",
                       data=rpm.datasets.stackloss())
selected = rpm.step_lmrobdet(full)

# Robust nested-model test
reduced = rpm.lmrobdet_mm("stack.loss ~ Air.Flow + Water.Temp",
                          data=rpm.datasets.stackloss())
test = rpm.rob_linear_test(full, reduced)

# Auto covariance dispatcher (MM if p<10 else Rocke)
rpm.cov_rob(rpm.datasets.glass().to_numpy())   # → MM
rpm.cov_rob(rpm.datasets.vehicle().to_numpy()) # → Rocke

# Lower-level S-PCA vs prcomp-shaped wrapper
rpm.pca_rob_s(rpm.datasets.wine().to_numpy(), k=3)
rpm.prcomp_rob(rpm.datasets.bus().to_numpy())
```

---

## 5. When Python ≠ full R surface

Use **`fit.to_r()`** or **`fit._r_fit`** when you need an unmapped R field.
Use **pandas preprocessing** for `subset` / `weights` / `na.action`.
For power-user access to internal R functions, call R directly via rpy2 —
but that bypasses the tested wrapper layer.
