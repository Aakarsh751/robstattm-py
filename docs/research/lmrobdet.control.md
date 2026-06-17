# lmrobdet.control

## 1. Statistical purpose
A **tuning-parameter container** consumed by `lmrobdetMM`, `lmrobdetDCML`, `step.lmrobdet`, and `rob.linear.test`. Centralizes choice of $\psi$-family, target efficiency, IRLS tolerances, max iterations, initial-estimator selection, and τ-correction toggles. Mirrors the role of `lm`'s `control = lm.control(...)` in classical regression.

## 2. Mathematical background
Encapsulates choices for the MM-fit pipeline (S step → M refinement → optional DCML). Each option corresponds to a hyperparameter in Maronna et al. (2019) Chapter 5.

## 3. R implementation
- File: `robstattm/RobStatTM-master/R/lmrobdet.R` line 454.
- Returns a named R list.
- Documented in `man/lmrobdet.control.Rd`. Large keyword surface (≥ 15 keys: `bb`, `efficiency`, `family`, `tuning.chi`, `tuning.psi`, `max.it`, `refine.tol`, `rel.tol`, `solve.tol`, `compute.rd`, etc.).

## 4. Inputs / Outputs / Return structure
A named R list — the wrapper should expose all keys as kwargs. Field map handled by `_converters.py`.

## 5. Dependencies
- RobStatTM only.

## 6. Python wrapper design
Exposed as both:
- A **dataclass** `LmrobdetControl` — public, IDE-discoverable.
- A **function** `lmrobdet_control(**kwargs) -> LmrobdetControl` — for users transcribing R code (R name with dot translated to underscore).

```python
@dataclass(frozen=True, slots=True)
class LmrobdetControl:
    bb: float = 0.5
    efficiency: float = 0.95
    family: Literal["mopt","bisquare","huber"] = "mopt"
    # ... full list from man/lmrobdet.control.Rd
```

`_converters.py` provides `lmrobdet_control_to_r(ctrl)` → R named list.

**Test:** assert `len(LmrobdetControl.__dataclass_fields__) == len(R("formals(lmrobdet.control)"))` to catch upstream API drift.

## 7. Validation strategy
- Field-by-field strict-tier match between `LmrobdetControl(...)` round-tripped through R and the direct `R("lmrobdet.control(...)")` call.
- Sweep every documented `family × efficiency` combination.
