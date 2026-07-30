# Implementation Rules

Mandatory ordering for every wrapper. **Do not skip steps.** Skipping leads to wrappers that look complete but have silent field-name drift or undocumented behavior.

---

## Before writing any wrapper code

1. **Understand the R source.**
   Open `robstattm/RobStatTM-master/R/<file>.R` and read the function end-to-end. Identify:
   - Input signature (formal arguments + defaults).
   - The shape and named elements of the return value (look for `list(...)` or the final expression).
   - Any internal calls into `pyinit`, `robustbase`, `rrcov`, or other RobStatTM internals.
   - Random-number usage (`runif`, `rnorm`, `sample`) and any `set.seed` call.

2. **Understand the return object.**
   Run, in an R session:
   ```r
   library(RobStatTM)
   fit <- <RFUN>(... small example ...)
   str(fit)
   names(fit)
   sapply(fit, class)
   ```
   Capture this into the function's `docs/research/<fn>.md` "R return structure" section. Field names here are authoritative for the Python dataclass.

3. **Identify dependencies.**
   Cross-check against `docs/dependency_map.md §3`. If a new external package is needed that the map does not list, **update the map first** in the same PR.

4. **Write/refresh `docs/research/<fn>.md`.**
   The research doc must answer all of: statistical purpose, theory pointer, R location, inputs, outputs, deps, helper functions, Python API design, edge cases, validation strategy. If the doc already exists, verify and amend.

5. **Write the test first** (TDD).
   - Use `templates/test_wrapper.py.tmpl`.
   - Cover all applicable cases from `docs/validation_strategy.md §3`.
   - Run pytest — it must fail for the right reason (wrapper not implemented).

6. **Write the wrapper.**
   - Use `templates/wrapper.py.tmpl`.
   - Conform to `docs/architecture.md §3` (dataclass, frozen, slots).
   - Conform to `docs/documentation_standards.md` (NumPy docstring with all required sections).

7. **Iterate until strict-tier green.**
   No tolerance loosening without a `decisions.md` entry.

8. **Update tracking.**
   - Append a session block to `project_memory/progress_log.md`.
   - Update the status columns in `docs/proposal_requirements.md §4`.
   - If this wrapper produces a plot, update `docs/plotting_strategy.md §3`.

---

## Rules that apply to all wrappers

- **Argument validation happens in Python, before the rpy2 boundary.** Catching bad shapes / dtypes in R yields opaque `RRuntimeError` messages.
- **All randomness goes through `robstattm_py.set_seed`.** Never call `np.random.seed` or `R("set.seed(…)")` directly inside a wrapper.
- **Never call `importr("RobStatTM")` at module import.** Use the `_r._get_pkg("RobStatTM")` lazy accessor.
- **No `from rpy2 import *`-style imports.** Use explicit `from rpy2 import robjects as ro`.
- **No silent type coercion.** If input is a list instead of an array, accept it via `np.asarray`; if input is the wrong dtype, raise `TypeError` with a clear message.
- **No catching `Exception`** at the wrapper level. Only catch the specific R/conversion errors you intend to translate.
- **Frozen dataclass — no mutation.** If a downstream caller needs to modify a field, they construct a new dataclass via `dataclasses.replace`.

---

## Prohibitions

- **Do not commit code without an accompanying test.**
- **Do not delete or rename anything in `robstattm/RobStatTM-master/`.** That tree is vendored upstream; we read it, we don't change it.
- **Do not vendor `pyinit`, `pense`, `GSE`** in the repo. Per `decisions.md D-003` they are user-installed CRAN packages.
- **Do not implement native-Python re-implementations during Phases 1–5.** They belong in Phase 6 stretch only (per proposal §8).
- **Do not loosen the default Strict tolerance tier** without a `decisions.md` entry and mentor confirmation.
- **Do not add fields to a dataclass beyond what the R return list provides.** Derived fields (e.g. `summary_table`) belong in helper methods, not the data dataclass.
