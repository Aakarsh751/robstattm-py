# API reference

Every function below wraps a RobStatTM routine and returns plain
NumPy / pandas / Python objects. Click a name for the full page: description,
parameters, return fields, result-object methods, and a runnable example.

> Python names are `snake_case` of the R names. Each wrapper is **also**
> available under its original R name via `robstattm_py.compat_r`
> (e.g. `from robstattm_py.compat_r import lmrobdetMM`).

## Univariate location & scale

| Function | R original | What it does |
|---|---|---|
| [`loc_scale_m`](wrappers/loc_scale_m.md) | `locScaleM` | Robust M-estimator of location **and** scale of a 1-D sample. |
| [`m_scale`](wrappers/m_scale.md) | `scaleM` | Robust M-estimator of scale (spread) alone. |

## Robust regression

| Function | R original | What it does |
|---|---|---|
| [`lmrobdet_mm`](wrappers/lmrobdet_mm.md) | `lmrobdetMM` | **The main robust regression**: MM-estimator with deterministic starts. |
| [`lmrobdet_dcml`](wrappers/lmrobdet_dcml.md) | `lmrobdetDCML` | DCML estimator, high efficiency, still robust. |
| [`lmrob_m`](wrappers/lmrob_m.md) | `lmrobM` | Plain M-estimator of regression (a simpler, faster robust fit). |
| [`step_lmrobdet`](wrappers/step_lmrobdet.md) | `step.lmrobdetMM` | Robust stepwise model selection by RFPE. |
| [`rob_linear_test`](wrappers/rob_linear_test.md) | `rob.linear.test` | Robust analogue of the F-test for nested models. |
| [`refine_sm`](wrappers/refine_sm.md) | `refine.sm` | Refinement (reweighting) iterations of an S-estimator. |
| [`invtr2`](wrappers/invtr2.md) | `INVTR2` | Inverse transform used in robust R² computation. |
| [`pyinit`](wrappers/pyinit.md) | `pyinit` | Peña-Yohai deterministic starting points for MM-regression. |
| [`lmrobdet_control`](wrappers/lmrobdet_control.md) | `lmrobdet.control` | Tuning object for `lmrobdet_mm` / `lmrobdet_dcml`. |
| [`lmrobm_control`](wrappers/lmrobm_control.md) | `lmrobM.control` | Tuning object for `lmrob_m`. |

## Robust covariance

| Function | R original | What it does |
|---|---|---|
| [`cov_rob`](wrappers/cov_rob.md) | `covRob` | **Auto-dispatcher**: picks MM or Rocke by dimension. Start here. |
| [`cov_rob_mm`](wrappers/cov_rob_mm.md) | `covRobMM` | MM-estimator of multivariate location & scatter. |
| [`cov_rob_rocke`](wrappers/cov_rob_rocke.md) | `covRobRocke` | Rocke S-estimator, efficient in higher dimensions. |
| [`cov_classic`](wrappers/cov_classic.md) | `covClassic` | Classical mean & covariance (a non-robust baseline). |
| [`kurt_sd_new`](wrappers/kurt_sd_new.md) | `KurtSDNew` | Kurtosis-based projection directions (estimator internals). |
| [`fastmve`](wrappers/fastmve.md) | `fastmve` | Minimum Volume Ellipsoid estimator (fast resampling start). |

## Robust PCA

| Function | R original | What it does |
|---|---|---|
| [`pca_rob_s`](wrappers/pca_rob_s.md) | `pcaRobS` | Robust PCA via M-scale minimisation. |
| [`prcomp_rob`](wrappers/prcomp_rob.md) | `prcompRob` | Robust PCA in the shape of base R's `prcomp`. |

## Robust GLM (logistic regression)

| Function | R original | What it does |
|---|---|---|
| [`by_logreg`](wrappers/by_logreg.md) | `BYlogreg` | Bianco-Yohai robust logistic regression. |
| [`wby_logreg`](wrappers/wby_logreg.md) | `WBYlogreg` | Weighted Bianco-Yohai (downweights leverage points). |
| [`wml_logreg`](wrappers/wml_logreg.md) | `WMLlogreg` | Weighted maximum-likelihood logistic regression. |

## External / stretch estimators

These wrap estimators that ship in **separate CRAN packages** (`pense`, `GSE`);
install them separately. See the [external estimators guide](../guides/external.md).

| Function | R original | What it does |
|---|---|---|
| [`pense`](../guides/external.md#pense) | `pense::pense` | Robust elastic-net S-estimator (full path). |
| [`pense_cv`](../guides/external.md#pense_cv) | `pense::pense_cv` | Robust elastic-net with cross-validation. |
| [`gse`](../guides/external.md#gse) | `GSE::GSE` | Generalized S-estimator with missing data. |
| [`tsgs`](../guides/external.md#tsgs) | `GSE::TSGS` | Two-step GSE for cell-wise outliers. |
| [`arima_rob`](../guides/external.md#arima_rob) | `robustarima::arima.rob` | Robust ARIMA (filtered tau-estimate). |
| [`var_comprob`](../guides/external.md#var_comprob) | `robustvarComp::varComprob` | Robust variance-component / mixed models. |
| [`glmrob`](../guides/external.md#glmrob) | `robustbase::glmrob` | Robust GLM (Poisson RQL/Mqle + MT). |
| [`cubinf`](../guides/external.md#cubinf) | `robcbi::cubinf` | CUBIF bounded-influence GLM. |

## See also

- **Datasets**, [`robstattm_py.datasets`](../guides/datasets.md)
- **ψ-loss families**, [`robstattm_py.psi`](../guides/psi-families.md)
- **External estimators**, [`pense`, `gse`, `tsgs`](../guides/external.md)
- **Setup & utilities**, [`check_setup`, `set_seed`, …](../guides/utilities.md)
- **Result-object methods**, [`.summary()`, `.predict()`, …](../guides/result-methods.md)

```{toctree}
:hidden:
:glob:

wrappers/*
```
