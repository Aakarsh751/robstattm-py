# Quality Gates

A wrapper is **NOT complete** until every box in this checklist is ticked.

This file is the canonical Definition of Done. The PR template includes it verbatim.

---

## Per-wrapper checklist

```
Wrapper: <python_name>  (wraps R <RFUN>)
PR:      #...

[ ]  R source reviewed                              — file:line cited in PR description
[ ]  R return structure captured                    — pasted into the vendored R source (see docs/RELOCATED.md)
[ ]  Dependency chain documented                    — docs/dependency_map.md §3 row updated
[ ]  the vendored R source (see docs/RELOCATED.md) written / refreshed      — all 7 required sections present
[ ]  Wrapper implemented                            — src/robstattm_py/<module>/<file>.py
[ ]  NumPy-style docstring                          — Parameters, Returns, Raises, Notes, References, Examples, See Also
[ ]  Frozen dataclass return type                   — per docs/architecture.md §3
[ ]  Argument validation before rpy2 boundary       — TypeError / ValueError raised pre-call
[ ]  R-call helpers used (no raw importr)           — _r._get_pkg, _r._rcall
[ ]  Unit tests pass                                — pytest tests/<module>/test_<file>.py -q
[ ]  Output matches R field-by-field (strict tier)  — atol=0, rtol=0 unless documented
[ ]  Coverage gate                                  — pytest --cov=src/robstattm_py/<module> --cov-fail-under=90
[ ]  Validation matrix cases covered                — cases 1–11 from docs/validation_strategy.md §3 as applicable
[ ]  Sphinx page builds without warnings            — sphinx-build -W -b html docs_sphinx/ _build/
[ ]  Example notebook updated                       — notebooks/<chapter>.ipynb runs top-to-bottom
[ ]  Plot helpers updated                           — project_memory/robstattm-py-planning-docs/plotting_strategy.md §3 row(s)
[ ]  progress_log.md session block appended         — project_memory/
[ ]  project_memory/robstattm-py-planning-docs/proposal_requirements.md §4 status updated     — wrapper/testing/doc columns set to ✅
[ ]  Architecture docs updated if applicable        — docs/architecture.md (only if a new pattern was introduced)
[ ]  No new files in archive/ moved or deleted
[ ]  No edits inside robstattm/RobStatTM-master/
```

---

## Phase-level exit gates

In addition to the per-wrapper checklist, each phase has an exit gate:

### End of Phase 1 (Week 2)
- All Phase-1 wrappers' checklists complete.
- `notebooks/ch2_loc_scale.ipynb` runs end-to-end in CI via `nbmake`.
- `pytest --cov=src/robstattm_py/univariate --cov-fail-under=90` green.

### End of Phase 2 / Midterm (Week 6)
- All regression wrappers' checklists complete.
- `notebooks/ch5_mineral.ipynb` reproduces Figs 5.1–5.7 against the R baselines.
- `pytest --cov=src/robstattm_py/regression --cov-fail-under=90` green.
- Midterm report written and accepted by mentors.

### End of Phase 3 (Week 10)
- All multivariate wrappers' checklists complete.
- `notebooks/ch6_wine.ipynb` reproduces Fig 6.3.
- `notebooks/ch6_bus.ipynb` reproduces Fig 6.10.
- Distance–distance and scree plot helpers shipped.
- `pytest --cov=src/robstattm_py/covariance --cov-fail-under=90` AND `pytest --cov=src/robstattm_py/pca --cov-fail-under=90` green.

### End of Phase 4 (Week 12)
- `notebooks/benchmarks.ipynb` published with timing and accuracy tables.
- Benchmark CSVs committed under `benchmarks/results/`.

### End of Phase 5 (Week 16)
- RTD site live with full API + examples gallery.
- PyPI `0.1.0` released.
- Install guide live; `robstattm_py.check_setup()` returns clean on at least one machine per OS.
- All tutorial notebooks polished.

### End of Phase 6 (Week 22) — Final submission
- Stretch wrappers (whichever landed) all have their per-wrapper checklists complete.
- Native-Python comparison documented in `notebooks/native_comparison.ipynb`.
- Final report in `docs/final_report.md`.
- Tagged release on GitHub and PyPI.

---

## What triggers a gate re-check

- Any upstream RobStatTM bump (CRAN releases > 1.0.12 during the GSoC window) requires re-running the strict-tier tests on the new version. Re-baseline only with mentor sign-off.
- Any rpy2 minor version bump requires re-running the entire test matrix.
- Any change to `_converters.py` requires re-running all field-by-field tests across all wrappers.
