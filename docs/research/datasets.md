# Datasets (all 20)

## 1. Statistical purpose
Each dataset reproduces an example from Maronna et al. (2019). Loaded as pandas DataFrames with R column names preserved.

## 2. R implementation
20 `.RData` files under `RobStatTM-master/data/`. Loaded in R via `data(<name>, package="RobStatTM")`. Documentation in `man/<name>.Rd`.

| Dataset | n | p | Type | Chapter | Used by |
|---------|---|---|------|---------|---------|
| `alcohol` | … | … | regression | 2 | textbook example |
| `algae` | … | … | regression | 5 | `algae.R` |
| `biochem` | … | … | regression | 4 | `biochem.R` |
| `breslow.dat` | … | … | GLM | 7 | textbook example |
| `bus` | … | … | PCA | 6 | `bus.R` Fig 6.10 |
| `flour` | … | … | regression | 4 | `flour.R` |
| `glass` | … | … | multivariate | 6 | textbook |
| `hearing` | … | … | regression | 5 | textbook |
| `image` | … | … | multivariate | 6 | textbook |
| `leuk.dat` | … | … | GLM | 7 | `leukemia.R` |
| `mineral` | … | … | regression | 5 | **flagship** `mineral.R` Figs 5.1–5.7 |
| `neuralgia` | … | … | GLM | 7 | textbook |
| `oats` | … | … | regression | 4 | `oats.R` |
| `resex` | … | … | regression | 2/4 | `resex.R` |
| `shock` | … | … | regression | 5 | `shock.R` |
| `skin` | … | … | GLM | 7 | `skin.R` |
| `stackloss` | … | … | regression | 4/5 | textbook |
| `vehicle` | … | … | multivariate | 6 | `vehicle.R` |
| `waste` | … | … | regression | 5 | textbook |
| `wine` | … | … | multivariate | 6 | **flagship** `wine.R` Fig 6.3 |

(Exact n / p filled in at implementation time by `str(data)` on each dataset.)

## 3. Python loader design
Single module `robstatm_py.datasets` with one function per dataset:

```python
def mineral() -> pd.DataFrame: ...
def wine() -> pd.DataFrame: ...
# ...
```

Underlying implementation (one helper for all):

```python
def _load(name: str) -> pd.DataFrame:
    pkg = _get_pkg("RobStatTM")
    R(f'data({name}, package="RobStatTM")')
    return r_to_pandas(R(name))
```

Each function:
- has the docstring lifted verbatim from `man/<name>.Rd` (parsed at package build time, stored in `_doc_strings.py`),
- caches the result so subsequent calls are O(1),
- normalizes column names: R `breslow.dat` → Python `breslow_dat()` returning a DataFrame whose columns are also underscore-normalized when they contain dots.

Also provides:

```python
robstatm_py.datasets.list()           # -> list[str] of all 20 names
robstatm_py.datasets.info(name)       # -> short description
robstatm_py.datasets.help(name)       # -> full docstring
```

## 4. Dependencies
RobStatTM only.

## 5. Validation strategy
- **Shape match**: `df.shape == R(f"dim({name})")`
- **Column names match**: ordered tuple of column names equal after R-dot → Python underscore translation
- **Value match**: strict-tier element-wise comparison via `numpy.testing.assert_array_equal` (datasets are constant, so this is trivially achievable)
- **Categorical levels match**: where R uses `factor`, Python returns `pd.Categorical` with the same `categories` order
