# Architecture — RobStatTM-Py

**Status:** design (pre-implementation).
**Constraints driving this design:** see `docs/proposal_requirements.md §2`.

---

## 1. High-level architecture

```
┌───────────────────────────────────────────────────────────────┐
│                   Python user (NumPy / pandas)                │
└──────────────────────────────┬────────────────────────────────┘
                               │ Python API
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                       robstattm_py  (this package)             │
│   ┌─────────────────┐  ┌────────────────┐  ┌───────────────┐  │
│   │  Public API     │  │  Converters    │  │ Result types  │  │
│   │  (function defs)│  │  np/pd ↔ R     │  │  (dataclasses)│  │
│   └────────┬────────┘  └────────┬───────┘  └───────▲───────┘  │
│            └──────────┬─────────┘                  │          │
│                       ▼                            │          │
│              ┌───────────────────┐                 │          │
│              │  R-call helpers   │─────────────────┘          │
│              │  (._rcall, ._extract, ._safe_set_seed)         │
│              └────────┬──────────┘                            │
└──────────────────────────┬────────────────────────────────────┘
                           │ rpy2.robjects
                           ▼
┌───────────────────────────────────────────────────────────────┐
│                          R runtime                            │
│   importr("RobStatTM"), importr("pyinit"), importr("rrcov"),  │
│   importr("robustbase"), importr("pense")?, importr("GSE")?   │
└───────────────────────────────────────────────────────────────┘
```

Each layer has one responsibility:

- **Public API** — argument parsing, NumPy-style docstrings, dataclass return.
- **Converters** — NumPy/pandas → R; R lists → Python dataclasses. Single place to apply field-name remapping (R `r.squared` → Python `r_squared`).
- **R-call helpers** — manage `set_conversion`, `set.seed`, deferred `importr`, error translation (`rpy2.rinterface.RRuntimeError` → `RobStatTMRError`).
- **Result types** — frozen `@dataclass` per estimator family; one source of truth for what the wrapper returns.

---

## 2. Package layout

```
robstattm_py/                          # importable package root
├── __init__.py                       # version, set_conversion patch, lazy importr
├── _r.py                             # singleton R bridge: importr cache, .rx2 helpers
├── _converters.py                    # np/pd → R, R → dict, dot/underscore name map
├── _errors.py                        # RobStatTMRError, RobStatTMSetupError
├── _typing.py                        # type aliases (ArrayLike, FormulaLike)
│
├── univariate/
│   ├── __init__.py                   # re-exports
│   ├── loc_scale_m.py                # locScaleM wrapper
│   └── m_scale.py                    # mScale wrapper
│
├── regression/
│   ├── __init__.py
│   ├── control.py                    # lmrobdet_control, lmrobm_control
│   ├── lmrobdet_mm.py                # lmrobdetMM
│   ├── lmrob_m.py                    # lmrobM
│   ├── lmrobdet_dcml.py              # lmrobdetDCML
│   ├── step.py                       # step_lmrobdet
│   ├── pyinit.py                     # pyinit wrapper
│   └── linear_test.py                # rob_linear_test
│
├── covariance/
│   ├── __init__.py
│   ├── cov_rob_mm.py                 # covRobMM
│   ├── cov_rob_rocke.py              # covRobRocke
│   └── kurt_sd_new.py                # KurtSDNew
│
├── pca/
│   ├── __init__.py
│   └── pca_rob_s.py                  # pcaRobS
│
├── glm/                              # Phase 6 stretch
│   ├── __init__.py
│   ├── by_logreg.py
│   ├── wby_logreg.py
│   └── wml_logreg.py
│
├── external/                         # Phase 6 stretch (separate R packages)
│   ├── __init__.py
│   ├── pense.py
│   ├── gse.py
│   └── tsgs.py
│
├── plotting/                         # Phase 3+ helpers
│   ├── __init__.py
│   ├── distance_distance.py
│   ├── residuals.py
│   └── scree.py
│
├── datasets/                         # thin loaders for vendored RobStatTM data
│   └── __init__.py                   # mineral(), wine(), bus() etc.
│
├── benchmarks/                       # Phase 4 — keeps benchmark code out of the wrapper path
│   ├── timing.py
│   └── synthetic.py
│
├── utils/
│   ├── check_setup.py                # robstattm_py.check_setup() entrypoint
│   └── seeds.py                      # set_seed(value) → both R and Python
│
└── py.typed                          # PEP 561 marker
```

**Public surface** (what `from robstattm_py import *` exposes): every wrapper plus `check_setup`, `set_seed`, the result dataclasses, and `__version__`. Nothing else.

**Tests** mirror the package tree:

```
tests/
├── conftest.py                       # R availability + fixture for set_seed
├── univariate/
│   ├── test_loc_scale_m.py
│   └── test_m_scale.py
├── regression/
│   ├── test_lmrobdet_mm.py
│   ├── test_lmrobdet_dcml.py
│   ├── test_step.py
│   └── test_pyinit.py
├── covariance/
│   ├── test_cov_rob_mm.py
│   └── test_cov_rob_rocke.py
├── pca/
│   └── test_pca_rob_s.py
└── integration/
    ├── test_mineral_reproduction.py
    ├── test_wine_reproduction.py
    └── test_bus_reproduction.py
```

---

## 3. Object design

### 3.1 Result dataclasses

One frozen dataclass per estimator family. Field names are **snake_case** versions of the R names, with the original R name preserved in the docstring.

Example (drafted — not implementation):

```python
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True, slots=True)
class LmrobdetMMResult:
    """Result of robstattm_py.regression.lmrobdet_mm().

    Fields map 1:1 to the named elements of R's lmrobdetMM() return list
    (see RobStatTM man page lmrobdetMM.Rd). R names with dots are converted
    to snake_case (e.g. R fitted.values -> fitted_values).
    """
    coefficients:  np.ndarray   # named in R; we drop names into .coef_names
    coef_names:    tuple[str, ...]
    scale:         float        # R: scalar
    residuals:     np.ndarray
    fitted_values: np.ndarray
    rweights:      np.ndarray
    r_squared:     float
    converged:     bool
    iter:          int
    control:       dict         # echo of the lmrobdet_control payload
    # ... full field list determined per-function in docs/research/<fn>.md
```

Why dataclass and not dict?
- Type-checkable; IDE autocomplete.
- Pickle-friendly for caching long benchmark runs.
- `slots=True` keeps memory low for the covariance/PCA cases that return matrices.
- Easy to extend (`@dataclass` inheritance for `summary()` views).

Why **frozen**?
- Wrapper outputs reflect a single R call's results — they should not mutate.

### 3.2 Errors

```python
class RobStatTMError(RuntimeError):
    """Base for all robstattm_py errors."""

class RobStatTMSetupError(RobStatTMError):
    """R is not installed, RobStatTM is missing, or rpy2 cannot start."""

class RobStatTMRError(RobStatTMError):
    """Raised when the underlying R call raises an error. Wraps the
    original RRuntimeError with the R traceback attached as .r_traceback."""
```

Translation happens in `_r.py` so every wrapper inherits it.

### 3.3 Type hints

- `ArrayLike = Union[np.ndarray, list, tuple]` (validated and `np.asarray`'d at the boundary).
- `FormulaLike = Union[str, "rpy2.robjects.Formula"]`.
- Returns are precise dataclasses, not `dict`.
- `py.typed` marker ships in the wheel.

### 3.4 Control objects

`lmrobdet_control(...)` and `lmrobm_control(...)` return a small dataclass that, when passed to a regression wrapper, is converted to an R `list` exactly matching the keys the R API expects. This gives Python users IDE autocomplete on tuning parameters without exposing rpy2 surface.

---

## 4. Error handling, validation, and seeding

| Concern | Where it lives | Behavior |
|---------|----------------|----------|
| Argument validation | inside each wrapper, before R call | Type / shape / NaN / categorical checks; raise `TypeError` / `ValueError` with a Python-style message **before** crossing the rpy2 boundary |
| R runtime error | `_r.py::_rcall` | `RRuntimeError` → `RobStatTMRError(msg, r_traceback=…)` |
| Missing R/package | `_r.py::_get_pkg` | `RobStatTMSetupError("RobStatTM not installed. Run install.packages('RobStatTM') in R, or call robstattm_py.check_setup() for details.")` |
| Reproducibility | `utils/seeds.py::set_seed(n)` | Calls both `np.random.seed(n)` and `R("set.seed(%d)" % n)` in one shot; tests always use this |
| Coercion warnings | `_converters.py` | Any silent coercion (e.g. `int → float`) logs at INFO level, never silently drops |

---

## 5. Lazy R startup

`from robstattm_py import lmrobdet_mm` must **not** start R — only `lmrobdet_mm(...)` does. Implementation: every wrapper's first line is `_r.RobStatTM` (a property that lazily calls `importr("RobStatTM")` once and caches it).

This keeps:
- doc builds (Sphinx autodoc) fast and offline,
- `import robstattm_py` cheap for unit tests that don't need R,
- error messages directed at the **first wrapper call**, not the import.

---

## 6. Naming conventions

| R name | Python public name | Where mapped |
|--------|--------------------|--------------|
| `lmrobdetMM` | `lmrobdet_mm` (module: `regression.lmrobdet_mm`) | `regression/__init__.py` |
| `lmrobdet.control` | `lmrobdet_control` | same |
| `step.lmrobdet` | `step_lmrobdet` | same |
| `covRobMM` | `cov_rob_mm` | `covariance/__init__.py` |
| `pcaRobS` | `pca_rob_s` | `pca/__init__.py` |
| `BYlogreg` / `WBYlogreg` / `WMLlogreg` | `by_logreg`, `wby_logreg`, `wml_logreg` | `glm/__init__.py` |
| return field `r.squared` | `.r_squared` | `_converters.py` field map |
| return field `fitted.values` | `.fitted_values` | same |

Aliases (`lmrobdetMM = lmrobdet_mm`, etc.) **may** be exposed at the top of each submodule for users transcribing R code. Decision deferred to mentor review (see `project_memory/decisions.md` D-005).

---

## 7. Threading and async

- `rpy2` is **not thread-safe**; the R interpreter is a singleton.
- Wrappers do not release the GIL.
- For benchmark parallelism we use **process-level** parallelism (subprocess per worker), not threads.

---

## 8. Out of scope for this document

- Plot rendering strategy → `docs/plotting_strategy.md`.
- Exact field-by-field field maps per function → `docs/research/<fn>.md` (one report per function).
- CI workflow YAML → drafted during Community Bonding, not now.
