# R ↔ Python Coverage Matrix

**Authoritative status of every `RobStatTM` R export against its Python wrapper.**
Generated 2026-06-11. Source of truth for "what's been ported".

The R column is the **exact** R-side name from the `RobStatTM` `NAMESPACE`
`export()` list (**47** callables, verified against
`robstattm/RobStatTM-master/NAMESPACE`). The Python column is what you type
after `import robstattm_py as rpm`. Note: `pyinit` lives in its own CRAN package
(a RobStatTM *dependency*), not in RobStatTM's NAMESPACE — it is wrapped for
convenience and reported separately by `check_setup()`.

Status legend:

| Symbol | Meaning |
|---|---|
| ✅ | Wrapped + tested strict-tier (`atol=0, rtol=0` against R) |
| ✅ alias | Alternative R name for the same underlying R function — Python wrapper resolves to the same callable |
| 🔒 | Intentionally not exposed (R-internal helper called by parent wrapper). See decision below. |

---

## Univariate (2 / 2)

| R name | Python | Status | Tests |
|---|---|---|---|
| `locScaleM` | `rpm.loc_scale_m` | ✅ | `tests/univariate/test_loc_scale_m.py` |
| `MLocDis` | `rpm.loc_scale_m` | ✅ alias | (covered above) |
| `scaleM` | `rpm.m_scale` | ✅ | `tests/univariate/test_m_scale.py` |
| `mscale` | `rpm.m_scale` | ✅ alias | (covered above) |

## Regression — main wrappers (5 / 5)

| R name | Python | Status | Tests |
|---|---|---|---|
| `lmrobdetMM` | `rpm.lmrobdet_mm` | ✅ | `tests/regression/test_lmrobdet_mm.py` |
| `lmrobdetDCML` | `rpm.lmrobdet_dcml` | ✅ | `tests/regression/test_lmrobdet_dcml.py` |
| `lmrobM` | `rpm.lmrob_m` | ✅ | `tests/regression/test_lmrob_m.py` |
| `pyinit` | `rpm.pyinit` | ✅ | `tests/regression/test_pyinit.py` |
| `step.lmrobdetMM` | `rpm.step_lmrobdet` | ✅ | `tests/regression/test_step.py` |

## Regression — companions (8 / 8)

| R name | Python | Status | Tests |
|---|---|---|---|
| `lmrobdet.control` | `rpm.lmrobdet_control` | ✅ | `tests/regression/test_control.py` |
| `lmrobM.control` | `rpm.lmrobm_control` | ✅ | `tests/regression/test_control_m.py` |
| `INVTR2` | `rpm.invtr2` | ✅ | `tests/regression/test_invtr2.py` |
| `rob.linear.test` | `rpm.rob_linear_test` | ✅ | `tests/regression/test_linear_test.py` |
| `lmrobdetLinTest` | `rpm.rob_linear_test` | ✅ alias | |
| `lsRobTestMM` | `rpm.rob_linear_test` | ✅ alias | (via compat_r) |
| `lmrobdetMM.RFPE` | `fit.rfpe()` method | ✅ | `tests/regression/test_lmrobdet_mm_methods.py` |
| `refine.sm` | `rpm.refine_sm` | ✅ | `tests/regression/test_refine_sm.py` |

## Regression — internal helpers (4, not exposed)

| R name | Python | Status | Why |
|---|---|---|---|
| `DCML` | — | 🔒 | Low-level core for `lmrobdetDCML`; takes pre-built `z, z0, control` arrays. End-users access via `lmrobdet_dcml`. |
| `cov.dcml` | — | 🔒 | Internal covariance step inside DCML. |
| `MMPY` | — | 🔒 | Internal MM-step inside `lmrobdetMM` (with CV split). |
| `SMPY` | — | 🔒 | Internal S+M-step inside `lmrobdetMM` (requires `split$x1/$x2`). |

These are deliberately not exposed (see decisions.md). Wrapping them as
public APIs would either require reimplementing the parent setup
(violates D-001) or accepting opaque R objects.

## Covariance (5 / 5)

| R name | Python | Status | Tests |
|---|---|---|---|
| `covRob` | `rpm.cov_rob` | ✅ (dispatcher) | `tests/covariance/test_cov_rob.py` |
| `Multirobu` | `rpm.cov_rob` | ✅ alias | |
| `covRobMM` | `rpm.cov_rob_mm` | ✅ | `tests/covariance/test_cov_rob_mm.py` |
| `MMultiSHR` | `rpm.cov_rob_mm` | ✅ alias | |
| `covRobRocke` | `rpm.cov_rob_rocke` | ✅ | `tests/covariance/test_cov_rob_rocke.py` |
| `RockeMulti` | `rpm.cov_rob_rocke` | ✅ alias | |
| `covClassic` | `rpm.cov_classic` | ✅ | `tests/covariance/test_cov_classic.py` |
| `KurtSDNew` | `rpm.kurt_sd_new` | ✅ | `tests/covariance/test_kurt_sd_new.py` |
| `initPP` | `rpm.kurt_sd_new` | ✅ alias | |
| `fastmve` | `rpm.fastmve` | ✅ | `tests/covariance/test_fastmve.py` |

## PCA (2 / 2)

| R name | Python | Status | Tests |
|---|---|---|---|
| `pcaRobS` | `rpm.pca_rob_s` | ✅ | `tests/pca/test_pca_rob_s.py` |
| `SMPCA` | `rpm.pca_rob_s` | ✅ alias | |
| `prcompRob` | `rpm.prcomp_rob` | ✅ | `tests/pca/test_prcomp_rob.py` + `test_pca_summaries.py` |

## GLM (3 / 3)

| R name | Python | Status | Tests |
|---|---|---|---|
| `BYlogreg` | `rpm.by_logreg` | ✅ | `tests/glm/test_logreg.py` |
| `logregBY` | `rpm.by_logreg` | ✅ alias | |
| `WBYlogreg` | `rpm.wby_logreg` | ✅ | `tests/glm/test_logreg.py` |
| `logregWBY` | `rpm.wby_logreg` | ✅ alias | |
| `WMLlogreg` | `rpm.wml_logreg` | ✅ | `tests/glm/test_logreg.py` |
| `logregWML` | `rpm.wml_logreg` | ✅ alias | |

## ψ-family helpers (9 / 9)

| R name | Python | Status | Tests |
|---|---|---|---|
| `bisquare` | `rpm.psi.bisquare` | ✅ | `tests/test_psi.py` |
| `huber` | `rpm.psi.huber` | ✅ | |
| `opt` | `rpm.psi.opt` | ✅ | |
| `optv0` | `rpm.psi.optv0` | ✅ | |
| `mopt` | `rpm.psi.mopt` | ✅ | |
| `moptv0` | `rpm.psi.moptv0` | ✅ | |
| `rho` | `rpm.psi.rho` | ✅ | |
| `rhoprime` | `rpm.psi.rhoprime` | ✅ | |
| `rhoprime2` | `rpm.psi.rhoprime2` | ✅ | |

## S3 methods (all 13 `S3method(...)` registrations in NAMESPACE)

Every S3 method registered by RobStatTM is ported — as a dataclass method when
it computes something, or as the result object's `__repr__` for the `print.*`
methods. `drop1.lmrobdetMM` was the last gap, closed 2026-06-14.

| R S3 method (NAMESPACE) | Python equivalent | Tests |
|---|---|---|
| `drop1.lmrobdetMM` | `fit.drop1()` / `rpm.drop1_lmrobdet(fit)` | `test_drop1.py` |
| `hatvalues.lmrob` (MM, DCML, M) | `fit.hatvalues()` | `test_lmrobm_methods.py`, `test_lmrobdet_mm_methods.py` |
| `print.lmrobdetMM` | `repr(fit)` | (via `__repr__`) |
| `print.lsRobTest` | `repr(rob_linear_test(...))` | (via `__repr__`) |
| `print.prcompRob` | `repr(prc)` | (via `__repr__`) |
| `print.summary.covClassic` | `repr(cov_fit.summary())` | (via `__repr__`) |
| `print.summary.covRob` | `repr(cov_fit.summary())` | (via `__repr__`) |
| `print.summary.lmrobdetMM` | `repr(fit.summary())` | (via `__repr__`) |
| `print.summary.prcompRob` | `repr(prc.summary())` | (via `__repr__`) |
| `summary.covClassic` | `cov_fit.summary()` | `test_cov_summaries.py` |
| `summary.covRob` | `cov_fit.summary()` | `test_cov_summaries.py` |
| `summary.lmrobdetMM` (also DCML, M) | `fit.summary()` | `test_lmrobdet_mm_methods.py`, `test_lmrobdet_dcml_methods.py` |
| `summary.prcompRob` | `prc.summary()` | `test_pca_summaries.py` |

`predict.lmrob` / `hatvalues.lmrob` come from robustbase via the `lmrob`
inheritance; both are exposed as `fit.predict(newdata)` / `fit.hatvalues()`
(with manual primitives for `lmrobM`, which lacks the `lmrob` parent).

## Datasets (20 / 20)

All 20 textbook datasets exposed as `rpm.datasets.<name>()`:
`alcohol, algae, biochem, breslow_dat, bus, flour, glass, hearing,
image, leuk_dat, mineral, neuralgia, oats, resex, shock, skin,
stackloss, vehicle, waste, wine`.
Returned as pandas DataFrames with R column names preserved in
`.attrs['r_columns']`. Tests in `tests/test_datasets.py`.

---

## Score

| Bucket | Wrapped | Exposed | Tested strict-tier |
|---|---|---|---|
| Core R callables (NAMESPACE) | 43 / 47 = **91%** | 43 (rest documented internal) | 43 |
| S3 methods | 13 / 13 = **100%** | 13 | 13 |
| Datasets | 20 / 20 = **100%** | 20 | 20 |
| ψ helpers | 9 / 9 = **100%** | 9 | 9 |
| Stretch external (pense/GSE/TSGS) | 4 / 4 = **100%** | 4 | 4 |

**Total unit test count: 454** (strict tier, atol=0, rtol=0 vs R), plus 13
notebooks executed end-to-end by `tests/test_notebooks.py`. `drop1.lmrobdetMM`
added 2026-06-14 (+15 tests, `tests/regression/test_drop1.py`) — it was the
final S3 gap, so **all 13 NAMESPACE S3 methods are now ported**. The
2026-06-14 custom-control parity fix (D-021) added `TestCustomControlS3Methods`
(+6 tests) confirming `summary`/`predict`/`hatvalues` reflect a non-default
control bit-for-bit vs R; the 2026-06-15 full-codebase audit (D-022) added
`TestCovClassicNaActionAndArgs` (+5 tests) after making `cov_classic`'s
`na_action` functional.

## Stretch — external packages (DONE 2026-06-13)

These live in separate CRAN packages (not RobStatTM) but are recommended
alongside it in Maronna et al. (2019). Wrapped per D-003 (user installs the
R package; `check_setup()` reports availability) and the D-015 policy of
wrapping only the named entry-point functions, not the whole packages.

| R name | Python | Status | Tests |
|---|---|---|---|
| `pense::pense` | `rpm.pense` | ✅ | `tests/external/test_pense.py` |
| `pense::pense_cv` | `rpm.pense_cv` | ✅ | `tests/external/test_pense.py` |
| `GSE::GSE` | `rpm.gse` | ✅ | `tests/external/test_gse.py` |
| `GSE::TSGS` | `rpm.tsgs` | ✅ | `tests/external/test_gse.py` |

Result dataclasses: `PenseResult`, `PenseCVResult`, `GSEResult`, `TSGSResult`,
all carrying the standard ergonomics (`to_dict` / `to_r` / `_repr_html_`).

**Verification (pense 2.5.2 / GSE 4.2-4 installed locally):**
- Both stochastic (PY initials / EMVE init) — `set_seed` Python+R parity
  confirmed bit-for-bit.
- `pense` coefficients pulled via R's own `coef(fit, lambda=...)` across the
  whole path; `pense_cv` via `coef(fit, lambda="min")`.
- `GSE`/`TSGS` return S4 objects; slots read via rpy2 `.slots[...]`; verified the
  public accessors (`getLocation` / `getScatter`) match the slot values.
- `GSE`/`TSGS` accept NaN (missing / filtered cells); `validate_2d_numeric`
  gained `allow_nan=True` for them (Inf still rejected).
- 35 strict-tier tests, auto-skipped via `needs_pense` / `needs_gse` when the R
  packages are absent.

**Updated coverage:** 46 / 46 RobStatTM-ecosystem callables now wrapped or
documented-internal, **plus** the 4 external stretch functions.

## Stretch — example-script externals (DONE 2026-06-21, D-024)

Wraps the remaining external packages that blocked example-script reproduction so
**all 26/26** `robstattm/examples-scripts/` scripts reproduce from Python. Same
entry-points-only / optional-install / strict-tier policy as above. Closes B-007.

| R name | Python | Package | Status | Tests |
|---|---|---|---|---|
| `robustarima::arima.rob` | `rpm.arima_rob` | `robustarima` | ✅ | `tests/external/test_arima_rob.py` |
| `robustvarComp::varComprob` | `rpm.var_comprob` | `robustvarComp` | ✅ | `tests/external/test_var_comprob.py` |
| `robustvarComp::varComprob.control` | `rpm.var_comprob_control` | `robustvarComp` | ✅ | `tests/external/test_var_comprob.py` |
| `robustbase::glmrob` | `rpm.glmrob` | `robustbase` (CORE) | ✅ | `tests/external/test_glmrob.py` |
| `robcbi::cubinf` | `rpm.cubinf` | `robcbi` (+`robeth`) | ✅ | `tests/external/test_cubinf.py` |

Result dataclasses: `ArimaRobResult`, `VarComprobResult`, `GlmrobResult`,
`CubinfResult` (+ `VarComprobControl`), all carrying the standard ergonomics.

**Verification (all installed locally — robustarima 0.2.7, robustvarComp 0.1-7,
robcbi 1.1.4 + robeth 2.7.8, robustbase 0.99-7):**
- `arima_rob`: deterministic; strict-tier on resex (p=2 seasonal), ar3 (p=3),
  MA1-AO (q=1) and the auto-AR path. Model list carries `ar` and/or `ma`.
- `var_comprob`: stochastic (`lmrob.S` / `TSGS` init) — `set_seed` parity
  confirmed; strict-tier on the autism Composite-Tau + Classic-S fits. A plain
  `data.frame` gives results numerically identical to `nlme::groupedData`
  (verified diff = 0). Whole-frame pandas2ri conversion is fragile, so the test
  rebuilds the frame column-by-column (bit-identical model matrix).
- `glmrob`: `method="Mqle"` (RQL) deterministic; `method="MT"` stochastic but
  seed-reproducible. `residuals()` is undefined for MT → wrapper falls back to the
  stored working residuals; `tcc`/`dispersion` are NULL for MT → NaN.
- `cubinf`: deterministic; strict-tier on the epilepsy design (`ufact=1.1`,
  `null.dev=FALSE`). `robcbi`/`robeth` are CRAN-archived (need Rtools on Windows).
- Strict-tier throughout (atol=0, rtol=0), auto-skipped via
  `needs_robustarima` / `needs_robustvarcomp` / `needs_wwgbook` / `needs_glmrob` /
  `needs_robcbi` when the R package is absent.

## Example-script coverage (updated 2026-08-11)

The claim above — that every R example script reproduces from Python — was
carried by the gallery notebooks, which consolidate several scripts per chapter.
It is now also carried **one-to-one** by [`examples/`](../examples/README.md):
25 Python scripts, one per script in `system.file("scripts", package =
"RobStatTM")`, each executed end to end on every CI runner by
`tests/test_examples.py`.

`wineDougtest.R` appears in the local `robstattm/examples-scripts/` copy but not
upstream, and is byte-identical to `wine.R` — hence 25 rather than 26.

Writing them surfaced four defects the wrapper tests had not found: formula
column names, `rob_linear_test`'s type guard, `cubinf` on an unnamed design
matrix, and R integer `NA` arriving as `-2147483648`. All four are fixed and
regression-tested (see the CHANGELOG). Worth recording as evidence for the
general point: a green suite is not the same as a working package. Each of those
four sat on a path no test exercised but every reader of the book would take.
