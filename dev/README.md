# dev/ — manual scratch & inspection scripts

Ad-hoc developer scripts used during implementation. They are **not** part of
the automated test suite (`tests/`) or the parity tier (`exploration/`) — they
are run by hand when debugging the R bridge or a specific wrapper.

- `_smoke_*.py` — quick end-to-end smoke checks for individual estimators
  (lmrobdet, DCML, step/linear-test, the UI/ergonomics surface).
- `_inspect_nb.py`, `_extract_nb_image.py` — notebook inspection helpers.
- `_inspect_rpy2_matrix.py` — probes how rpy2 converts a given R matrix
  (handy when chasing the numpy2ri shape/`dim`-attribute gotchas).

Run them directly, e.g.:

```bash
python dev/_smoke_check.py
```

They were moved here from `tests/` (where their `_`-prefix kept pytest from
collecting them) to keep the test tree limited to real, collected tests.
