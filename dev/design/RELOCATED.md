# Relocated planning documents

These files used to live in `docs/`. They recorded how the package was planned
and built rather than how it works, they were already excluded from the
published site, and `docs/research/*.md` had drifted out of step with the code
(the authoritative reference for R behaviour is the vendored R source, not those
notes). Keeping stale internal notes inside a repo people are about to install
from invites someone to read them as documentation.

They were **moved, not deleted** — project history is worth keeping. They now
live outside the package repo, in:

    <workspace>/project_memory/robstattm-py-planning-docs/

with this content:

| File | What it recorded |
|---|---|
| `implementation_plan.md` | Build order and critical path |
| `notebook_plan.md` | Which example scripts each gallery notebook covers |
| `documentation_plan.md` | Documentation milestones |
| `coverage_gap_analysis.md` | Which R functions were not yet wrapped, and why |
| `plotting_strategy.md` | Path A (R device) vs native plotting, decision D-008 |
| `plotting_suite_plan.md` | Design of `robstattm_py.plot`, decision D-023 |
| `proposal_requirements.md` | The GSoC proposal's requirements, traced to deliverables |
| `research/*.md` | Per-function R return-structure notes, written during implementation |

## What to use instead

- **R behaviour, defaults, return fields** — read the vendored R source under
  `robstattm/RobStatTM-master/R/`, and `formals()` on the installed package.
  That is the only source that cannot be stale.
- **What the package covers** — [`coverage_matrix.md`](coverage_matrix.md).
- **How it is put together** — [`architecture.md`](architecture.md) and
  [`user_interface.md`](user_interface.md).
- **How to add a wrapper** — [`implementation_rules.md`](implementation_rules.md)
  and [`quality_gates.md`](quality_gates.md).
- **Worked examples of every book script** — [`../examples/`](../examples/).
