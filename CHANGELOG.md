# Changelog

Notable changes to RobStatTM-Py. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

_Nothing yet._

## [0.1.0] — 2026-08-12

First release published to PyPI.

> Version 0.1.0 was prepared on 2026-08-10 but never tagged or published. The
> entries below are therefore all part of it: the production audit first, then
> the release engineering that preceded it.

### Added

- **`examples/` — a runnable Python script for every RobStatTM example script.**
  All 25 scripts from `system.file("scripts", package = "RobStatTM")`, covering
  Chapters 2 and 4–8 of Maronna et al. plus both vignettes. Each preserves its
  source's structure, example numbers and figure numbers. Every one is executed
  end to end by `tests/test_examples.py`; a script needing an absent optional R
  package exits 77 with an install line and is reported as a skip naming the
  package, never as a pass. New `[examples]` extra (matplotlib, scipy) for the
  non-robust comparators the R scripts plot alongside the robust fits.

### Fixed

- **A formula may use the column names you can actually see.** The dataset
  loaders rename R's dotted columns for Python (`n.shocks` → `n_shocks`), but
  the frame is pushed to R under its original names, so the obvious call —
  read the frame, look at `df.columns`, write a formula — failed with R's
  `object 'n_shocks' not found`, naming something the caller never typed. Both
  spellings now work and give identical fits.
- **`rob_linear_test` accepts `lmrob_m` fits, as R does.** R's
  `rob.linear.test` takes `lmrobdetMM` *or* `lmrobM` objects, its own help-page
  example uses `lmrobM`, and so does the book's Example 4.2 — which the wrapper's
  type check made impossible to reproduce. Each fit is now also replayed in R
  with the estimator that produced it; refitting an M fit as MM would have
  returned a plausible number for the wrong pair of models.
- **R's integer `NA` no longer arrives as the number `-2147483648`.** R stores
  integer `NA` as `INT_MIN`, and rpy2's pandas conversion maps the column to
  numpy `int32`, which has no missing value — so the sentinel came through as
  ordinary data. Nothing raised and nothing warned; `mean()`, `min()` and
  `dropna()` were simply wrong. Affected columns now become pandas `Int64` with
  real missing values.
- **`cubinf` no longer crashes on an unnamed design matrix.** `names()` on an
  unnamed R vector returns `NULL`, which rpy2 hands back as a `NULLType` — not
  `None`, and not sized — so the length check raised `TypeError`. This was the
  common case, not an edge case: it made `cubinf` unusable from the `(X, y)`
  form entirely.
- **`datasets.info()` no longer raises on a Windows console.** It contained `≈`,
  which is outside cp1252, so simply printing it raised `UnicodeEncodeError`
  whenever stdout was a pipe. Dataset descriptions are ASCII now, and a test
  holds the line.
- `robstattm-py setup`'s "already running" error now names `--force-unlock`, so
  a lock left behind by a killed process is recoverable rather than a six-hour
  wait.
- `robstattm-py info` no longer claims this package sets `RPY2_CFFI_MODE`. It
  never did; the variable is read by rpy2 and set by the user.

### Changed

- **Lint is enforced in CI.** `ruff check` was documented in CONTRIBUTING but
  never run by any workflow, and had accumulated roughly 790 findings — one of
  them a genuinely undefined name in `src/`. The tree is clean; deliberate
  exceptions are recorded in `pyproject.toml`'s `per-file-ignores` with the
  reason beside each (R-parity argument names like `X` and `Sigma`, the R-name
  aliases in `compat_r`, the domain-ordered imports in `__init__`).
- `fit.plot_residuals()`, `.plot_qq()` and `.plot_diagnostics()` now appear in
  the generated API tables. They were missing only because the mixins had no
  docstrings, which is what the generator selects on.

### Removed

- Dead code: `_r.to_py`, `_r._ensure_windows_r_dll_path` (whose docstring
  claimed a reference that did not exist), `_converters.py_to_r_field_name` /
  `r_to_py_field_name`, `_renv.state.clear_lock` (superseded by
  `--force-unlock`), `_renv.paths.current_root_env`,
  `_renv.activate.force_abi_mode` (never called, and the behaviour it described
  was documented to users as automatic), and an unreachable `_VECTOR_FAMILIES`
  set. Plus eleven unused imports.
- Planning documents moved out of the package repo to
  `project_memory/robstattm-py-planning-docs/` — see `docs/RELOCATED.md`. They
  recorded how the package was built rather than how it works, were already
  excluded from the published site, and `docs/research/*.md` had drifted out of
  step with the code.

---

### Added — release engineering (prepared 2026-08-10)

**R is found automatically, or installed for you.**

- `robstattm-py setup` downloads a private R (R + RobStatTM from conda-forge)
  into a directory this package owns, leaving any existing R untouched. You no
  longer need to install R yourself.
- R is located without configuration on every platform: `ROBSTATTM_R_HOME`, the
  private environment, `R_HOME`, conda prefixes, `PATH`, the Windows registry,
  and the conventional install roots for each OS. Setting `R_HOME` by hand is no
  longer necessary anywhere, including Windows.
- An R built for the wrong CPU architecture is detected by parsing its shared
  library's PE/ELF/Mach-O header and rejected with a clear message, rather than
  terminating the Python process — which is what loading it would otherwise do.
- When no R is found, the error lists every location searched and why each was
  rejected.

**A command-line interface**, `robstattm-py` (also `python -m robstattm_py.cli`):

- `setup` — install a private R
- `doctor` — diagnose Python, rpy2, R and the R packages; `--json` for scripting
- `info` — show paths and settings; never starts R, always exits 0
- `install-r-packages` — install R packages without an R console
- `uninstall` — remove what was installed, never anything else

Documented exit codes, and every error carries a concrete remedy.

**Documentation** for people who are not already fluent in both languages:

- *Install in 10 minutes* — assumes no terminal, Python or R experience
- *Coming from R* — the complete R-to-Python translation
- *Platform support* — what works where, including what does not
- *Checking your install* — verifying things, and reading errors
- *Troubleshooting* — symptom-by-symptom fixes

### Fixed — release engineering

- `cov_rob`, `cov_rob_rocke` and `kurt_sd_new` failed when called first in a
  session. RobStatTM's `KurtSDNew.R:42` reads `.Random.seed` unconditionally,
  and R does not create it until the RNG is used; an embedded rpy2 session is
  pristine. R's RNG is now initialised at startup with `set.seed(NULL)`, which
  leaves results random. *(Upstream issue; to be reported.)*
- Importing rpy2 against an R with no shell crashed with `IndexError`.
  rpy2 indexes empty `R CMD config` output and guards only
  `CalledProcessError`. This bit exactly the users who had both a provisioned
  and a system R. Translated to the error rpy2 already handles.
- `check_setup()` reported `rpy2: unknown` on every current install — rpy2 3.6
  removed `rpy2.__version__`. Now read from package metadata.
- Console output used em dashes that render as replacement characters on
  Windows `cp1252` consoles, including `check_setup`'s own result line.
- The package status table misaligned once a name exceeded 12 characters
  (`robustvarComp` is 13).
- On Windows, provisioning is refused up front when the install path would
  exceed the 260-character limit, with a copy-pasteable fix, instead of failing
  several minutes into a download with an opaque "Package cache error".
- All 17 example notebooks hardcoded `C:\Program Files\R\R-4.5.2`, so they only
  ran on one machine. Removed; R is found automatically.
- **macOS**: provisioning failed out of the box. R's launcher script expands
  its own path unquoted, so the space in `~/Library/Application Support`
  stopped R from starting. The private R now lives in `~/.robstattm-py`, and
  a space anywhere in the install path is refused before anything is
  downloaded.
- `robstattm-py doctor --json` could emit unparseable output. Both rpy2 and R
  itself write to stdout while R starts; that text is now captured (at the
  file-descriptor level, since R writes from C) and re-emitted on stderr.

### Changed — release engineering

- **Renamed** from `robstatm-py` to `robstattm-py` (import `robstattm_py`) to
  match the spelling of the upstream R package RobStatTM. There are no previous
  releases, so no compatibility shim is provided.
- `check_setup()` and `robstattm-py doctor` share one source of truth for the R
  package lists.
- "R package not installed" errors now suggest `robstattm-py
  install-r-packages`, which works for users who have no R console.

### Known limitations

- **Apple Silicon, ARM Linux and POWER Linux**: conda-forge has no
  `r-robstattm` or `r-pyinit` build for `osx-arm64`, `linux-aarch64` or
  `linux-ppc64le`, so `setup` compiles those two from CRAN source (10–15
  minutes; on macOS it also needs the Xcode command line tools). Everything
  works afterwards — Apple Silicon provisioning is verified in CI. See
  *Platform support*.
- `pense` and `GSE` are not on conda-forge and are not installed by `setup`;
  use `robstattm-py install-r-packages pense GSE`.
- `robcbi` is archived on CRAN, so the `cubinf` wrapper cannot be exercised
  without building it from the CRAN archive.

[Unreleased]: https://github.com/Aakarsh751/robstattm-py/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Aakarsh751/robstattm-py/releases/tag/v0.1.0
