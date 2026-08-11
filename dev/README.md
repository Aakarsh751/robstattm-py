# dev/ — manual scratch & inspection scripts

Developer scripts run by hand when debugging the R bridge, a wrapper, or the
build. They are **not** part of the automated suite (`tests/`) or the parity
tier (`exploration/`), and they are pruned from the sdist.

Anything here that can be expressed as a test belongs in `tests/` instead — a
check that only runs when someone remembers to run it is worth very little.
What survives is what genuinely cannot be a test: things CI invokes directly,
and probes whose output a human has to read.

## Called by CI

- `_assert_doctor.py` — asserts `doctor --json` reports the expected R source
  (`ci.yml`). Without it, a provisioning bug could make every leg silently test
  the same code path.
- `_solve_check.py` — cross-platform conda solve check (`provision.yml`).
- `_check_all_doc_code.py` — executes the code in every documentation page.

## Verification, run before a release

- `_verify_discovery_scenarios.py` — the same fit with `R_HOME` set, with only
  `PATH`, and with R hidden from `PATH`; asserts all three agree bit-for-bit.
  Each runs in its own process because rpy2 binds to an R at first import.
- `_verify_wheel_install.py` — proves the built *wheel* works from a clean venv,
  not merely the source checkout.

## Smoke checks

`_smoke_check.py`, `_smoke_dcml.py`, `_smoke_lmrobdet.py`, `_smoke_step_rlt.py`,
`_smoke_ergonomics.py`, `_smoke_ui_phase2.py`, `_ui_demo.py` — quick end-to-end
runs of one estimator family. Largely superseded by `tests/` and by
`examples/`; kept because they print human-shaped output when a fit is
behaving strangely and you want to look at it rather than assert on it.

## Probes

- `_inspect_rpy2_matrix.py` — how rpy2 converts a given R matrix (for the
  numpy2ri shape / `dim`-attribute gotchas).
- `_inspect_nb.py`, `_extract_nb_image.py` — notebook inspection.
- `_audit_symbols.py` — reports symbols defined in `src/` that nothing outside
  their own file references. **Advisory**: it matches text, so it over-reports,
  and every candidate still has to be read in context before it is touched. It
  found six genuinely dead functions in the 2026-08-11 audit.
- `_check_cp1252.py` — reports runtime string literals that a Windows cp1252
  console cannot encode. Also **advisory**: it cannot see that `check_setup`
  and `doctor` already guard their status glyphs by probing `stdout.encoding`,
  so most of what it reports is fine. The one real bug it found is now covered
  by `tests/datasets/test_printable.py`.

## Notebook build

- `build_new_notebooks.py` — regenerates the ch6-autism / ch7-epilepsy / ch8
  gallery notebooks.

Run any of them directly:

```bash
python dev/_smoke_check.py
```
