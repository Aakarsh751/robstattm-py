# Data Pipelines Catalog

Catalog of every synthetic-data and alternate-source scenario in the
2026-06-15 test campaign, the wrappers each one exercises, and the R fields
compared. Every scenario pushes the **same** data to R and asserts bit-identical
outputs (`atol=0, rtol=0`); stochastic estimators are seeded on both sides.

Helpers: `exploration/_synth.py` — generators (`make_regression_df`,
`make_cov_data`, `make_binary_xy`, `make_univariate`) and R plumbing
(`push_to_r`, `reval`, `rm_r`).

> **Why this is exact.** `numpy.float64 → R double` and `float64 pandas column →
> R data.frame double` are IEEE-754 lossless, so pushing one array to both sides
> gives identical inputs. The Python wrapper *is* R under the hood, so identical
> inputs + identical RNG state (seeded both sides) ⇒ bit-for-bit equality.

---

## A. Synthetic pipelines (`test_synthetic_pipelines.py`)

Data is generated with `numpy.random.default_rng(seed)` (a stream independent of
R's RNG, so the data is fixed regardless of any seeding).

| # | Scenario (synthetic data)                                  | Wrapper(s)                                   | Parameters swept                  | R fields compared                                  |
|---|------------------------------------------------------------|----------------------------------------------|-----------------------------------|----------------------------------------------------|
| 1 | 1-D Gaussian (n≈45) + 12% gross outliers                   | `loc_scale_m`                                | psi ∈ {mopt,bisquare,huber} × eff ∈ {0.90,0.95} | `mu`, `std.mu`, `disper`                |
| 2 | 1-D Gaussian (n≈50) + 10% gross outliers                   | `m_scale`                                    | family ∈ {bisquare,mopt,opt} × delta ∈ {0.5,0.25} | scalar M-scale                          |
| 3 | 1-D uniform grid on [-4,4]                                  | `psi.rho` / `rhoprime` / `rhoprime2`         | family ∈ {bisquare,opt,mopt}      | elementwise ρ, ψ=ρ′, ρ″                            |
| 4 | scalar RR² + bisquare cc                                    | `invtr2`                                      | rr2 ∈ {0.3,0.5,0.75}              | scalar `INVTR2`                                    |
| 5 | n=70, p=3 linear model + 10% vertical outliers             | `lmrobdet_mm`, `lmrobdet_dcml`, `lmrob_m`    | estimator                         | coef, scale, fitted.values, residuals, cov         |
| 6 | n=80, p=2 + 15% outliers + leverage                        | `lmrobdet_mm` (custom control)               | family/eff ∈ {(bisquare,0.85),(mopt,0.95)} | coef, scale, fitted.values                |
| 7 | n=60, p=3 + 8% outliers                                    | `lmrobdet_mm` (X/y vs formula vs R)          | —                                 | coef (3-way identity)                              |
| 8 | n=90, p=5 correlated + 10% row contamination               | `cov_rob_mm`                                  | corr ∈ {False,True}               | center, cov, dist, (cor)                           |
| 9 | n=120, p=12 correlated + 8% contamination                  | `cov_rob_rocke`                               | —                                 | center, cov, dist                                  |
| 10| n∈{90,120}, p∈{6,12}                                       | `cov_rob` (auto dispatch)                     | p → MM vs Rocke                   | estimator_type, center, cov                        |
| 11| n=70, p=4 correlated                                       | `cov_classic`                                 | corr ∈ {False,True}               | center, cov, (cor)                                 |
| 12| n=80, p=4 + 5% contamination                               | `fastmve`                                     | —                                 | center, cov, scale                                 |
| 13| n=85, p=5 + 6% contamination                               | `kurt_sd_new`                                 | —                                 | center, cova                                       |
| 14| n=100, p=6 + 7% contamination                              | `prcomp_rob`                                  | rank=4                            | sdev, rotation, center                             |
| 15| n=110, p=6 + 5% contamination                              | `pca_rob_s`                                   | ncomp=3                           | eigvec, mu, propex, propSPC                        |
| 16| binary GLM n=140, p=3 + 5% mislabelled outliers            | `by_logreg`, `wby_logreg`, `wml_logreg`      | method                            | coef, standard.deviation, fitted.values, residual.deviances |
| 17| n=60, p=2 linear model (intercept design)                  | `refine_sm`                                   | family=bisquare, step=M           | beta.rw, scale.rw                                  |
| 18| n=60, p=6 sparse-β linear model + 10% outliers             | `pense` (+ path coef via `coef()`)           | alpha ∈ {0.5,1.0}                 | lambda path, coefficient path                      |
| 19| n=90, p=5 Gaussian + 5% MCAR missingness                   | `gse`                                         | —                                 | mu (`getLocation`), cov (`getScatter`)             |

## B. Data-ingress pipelines (`test_data_ingress.py`)

Models how a real Python user gets data in; the **fully preprocessed** frame is
pushed to R, so "arrived via path X" ≡ "native R" is what's proven.

| # | Ingress path                                  | Preprocessing                                | Wrapper        | R fields compared            |
|---|-----------------------------------------------|----------------------------------------------|----------------|------------------------------|
| 1 | pandas → `to_csv` → `pd.read_csv` → `astype`  | dtype cast                                   | `lmrobdet_mm`  | coef, scale, fitted.values   |
| 2 | `sklearn.datasets.load_diabetes`              | 3-feature frame + injected outliers          | `lmrobdet_mm`  | coef, scale                  |
| 3 | `sklearn.datasets.load_iris`                  | 150×4 feature matrix                         | `cov_rob_mm`   | center, cov                  |
| 4 | `sklearn.datasets.make_classification`        | binary y pulled from frame columns           | `wby_logreg`   | coef, fitted.values          |
| 5 | `datasets.load("robustbase","coleman")`       | dot-free R names, `Y ~ .`                     | `lmrobdet_mm`  | coef, scale, residuals       |
| 6 | messy frame → rename/dropna/query/astype      | full pandas clean (rows actually dropped)    | `lmrobdet_mm`  | coef, scale                  |
| 7 | two frames → `merge(on="id")`                 | join then drop key                           | `lmrob_m`      | coef, scale                  |

## C. Edge cases (`test_edge_cases.py`)

Faithful to R: assert the *wrapped* error where R errors, assert *bit-parity*
where R succeeds.

| Input pathology                          | Wrapper(s)                                  | Expected behavior                                   |
|------------------------------------------|---------------------------------------------|-----------------------------------------------------|
| NaN / Inf entry                          | loc_scale_m, cov_rob_mm, cov_classic, cov_rob, prcomp_rob, by_logreg | clean `ValueError` (caught before R)    |
| constant (zero-variance) column          | cov_rob_mm, cov_classic                     | clean `RobStatTMRError` (singular)                  |
| single column (p=1)                      | cov_rob_mm, prcomp_rob                       | clean `RobStatTMRError`                             |
| p > n                                    | cov_rob_mm                                   | clean `RobStatTMRError` (not positive definite)     |
| exact collinear predictor (rank-deficient)| lmrobdet_mm                                 | **bit-parity** with R — dropped term is `NaN`       |
| perfect separation                       | by_logreg                                    | **bit-parity** with R (full field set)              |
| perfect separation                       | wby_logreg                                   | raises (rough edge — **B-009**: R returns truncated object) |
| bad `type=` / `delta` out of range / empty / X-y length / non-binary y / mixed invocation | various | clean `ValueError` / `TypeError`        |

---

## Promotion criteria

A scenario graduates from here into `tests/` when it is **stable, fast, and
deterministic** (seeded on both sides), per `exploration/TESTING.md`. The
synthetic full-field parity cases (A.5–A.16) are the strongest promotion
candidates — they assert every numeric field, not just shapes. Hold until
blocker **B-009** is resolved before promoting any WBYlogreg-separation case.
