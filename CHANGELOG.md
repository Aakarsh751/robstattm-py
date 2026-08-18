# Changelog

Notable changes to RobStatTM-Py. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/).

## [0.1.0], 2026-08-18

First release published to PyPI.

### Added

- **`setup` now asks what you want instead of always downloading.** On a real
  terminal it shows a short numbered menu: if an R is already installed it
  offers to *use that R* (the recommended default, nothing to download) or to
  download a private R anyway; if no R is found it offers to download one or to
  point at an R you have elsewhere. Non-interactive use (scripts, CI, `--yes`,
  `--dry-run`, `--force`) is unchanged and still provisions without prompting.
- **Installer coverage for uv, pipx, and conda.** The install guide documents
  installing with `uv` and `pipx` alongside `pip` (the package is a standard
  PEP 621 / setuptools project, so `uv build` and `uv pip install` work with no
  special flags), and `packaging/conda/` holds a draft conda-forge recipe.
- **House-style guard against em dashes** (`dev/_check_no_emdash.py`), run in CI.

### Changed

- **Repo layout: contributor-facing design docs moved from `docs/` to
  `dev/design/`,** so the docs tree holds only user-facing pages. The six
  per-family `_smoke_*.py` scripts and `_ui_demo.py` were removed; `verify.py`
  already covers every estimator family end to end.
- **Em dashes removed repo-wide** in favour of ordinary punctuation, including
  at the source of the generated API pages.

### Fixed

- **Colab/Kaggle: "cannot import name 'default_converter' from 'rpy2.robjects'
  (unknown location)" is now diagnosed correctly.** The real cause, confirmed on
  a live Colab, is **not** the rpy2 binding or which R loads: rpy2 3.6 is split
  across three separately-versioned distributions (`rpy2`, `rpy2-rinterface`,
  `rpy2-robjects`) and Colab/Kaggle sometimes ship them out of step (observed:
  `3.6.7 / 3.6.6 / 3.6.5`), which turns `rpy2.robjects` into an empty namespace
  package with no file. The setup error used to blame a binding/R mismatch and
  send readers down `RPY2_CFFI_MODE=ABI`, a dead end for this. It now detects the
  `(unknown location)` signature, prints the three installed versions as evidence,
  and gives the fix: `pip install --force-reinstall --no-cache-dir rpy2` then
  restart. The new Colab/Kaggle quickstart runs that reinstall up front, so a
  plain install + import + fit works against the platform's own R (`/usr/lib/R`),
  no `setup` and no 400 MB download.
  (Supersedes two interim attempts this cycle that misread the failure as a
  binding problem, one forcing ABI on hosted notebooks, since reverted, and one
  gating ABI on a `find_spec` probe that proved unreliable. The automatic ABI
  selection is unchanged from 0.1.0: it applies only to a *provisioned* R.)
- **"No usable R installation was found" pointed at a command that may not be on
  PATH.** The remedy said to run `robstattm-py setup`, but pip frequently installs
  that script into a directory Windows does not have on `PATH`, so the one user
  who most needs it hits a second dead end. The message now also gives the
  identical, always-available `python -m robstattm_py.cli setup`.

- **Windows: `setup` could fail at "[4/4] Verifying" with a mingw
  pseudo-relocation error.** Reported from a real machine. Steps 1–3 copy files
  and succeed; step 4 is the first thing that actually *starts* R, so a DLL
  loading problem surfaces there and looks like a bad download.

  Windows resolves a DLL by scanning `PATH` left to right and taking the first
  name match. R needs `R.dll`, `Rblas.dll` and a mingw runtime, names that a
  CRAN R installation, Rtools, MSYS2, Git's bundled mingw and other conda
  environments also ship. `run_in_env` had left `PATH` entirely to
  `micromamba run`'s activation; it now puts the environment's own directories
  in front itself, so an incomplete activation cannot cause this.

  The same ordering bug existed on the *runtime* path:
  `validate._bin_dirs_for` listed `Library/bin` before
  `Library/mingw-w64/bin` (both can hold the same runtime DLL, and the first
  match wins) and omitted `Scripts` entirely. Both now follow conda's own
  activation order.

  Verified by induction, with a CRAN R and Rtools ahead on `PATH`, a bare
  `Rscript` launch exits `0xC0000135` and the shipped code loads all four R
  packages against the same `PATH` (`dev/_verify_dll_fix.py`).
- **"rpy2 is not installed" was reported on machines where rpy2 *was*
  installed.** Reported from Google Colab, where one `doctor` run printed
  `rpy2 version 3.6.7` and, below it, `could not be started: rpy2 is not
  installed`. Importing `rpy2.robjects` both imports a package and *starts R*,
  and both raise `ImportError`; the handler assumed the first, asserted it as
  fact, and discarded the message that said what had actually failed.

  It now checks whether rpy2 is importable before claiming it is missing, and
  otherwise reports an R-loading failure quoting rpy2's own error, the R it
  tried to load, and the binding mode in effect.

  The usual cause is rpy2's compiled binding having been built against a
  different R than the one being loaded, normal wherever rpy2 arrives prebuilt
  (Colab, a distro package) and the R is one we provisioned. rpy2's ABI binding
  is immune, so it is now chosen **before rpy2 is imported** whenever the R
  being loaded is one `robstattm-py setup` provisioned. A system R keeps the
  faster compiled binding.

  Chosen up front rather than retried after a failure, because there is no valid
  retry: rpy2 embeds R as a process-global singleton, so once an import has
  attempted to load R the attempt cannot be undone. An earlier version of this
  fix did retry, purging `sys.modules` and re-importing, and on Colab it
  printed a reassuring "fell back to ABI" warning and then failed on the next
  line with `cannot import name 'default_converter' from 'rpy2.robjects'
  (unknown location)`, a module with no `__file__`. That was worse than the bug
  it replaced, because it also destroyed the evidence.

- **The advice for that failure was actively wrong.** It said to re-run with
  `--force`, which re-downloads several minutes and a gigabyte of bytes that
  were already correct, and fails identically. New `RStartupError` explains the
  DLL mechanism and offers `--use-system-r`, a clean `PATH`, and
  `ROBSTATTM_R_HOME`, and says plainly that `--force` will not help.

### Earlier 0.1.0 work (2026-08-10 to 08-12)

> Prepared on 2026-08-10 but never tagged or published, so these entries are part
> of the same 0.1.0 release above: the production audit first, then the release
> engineering that preceded it.

### Added

- **`examples/`, a runnable Python script for every RobStatTM example script.**
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
  the frame is pushed to R under its original names, so the obvious call,
  read the frame, look at `df.columns`, write a formula, failed with R's
  `object 'n_shocks' not found`, naming something the caller never typed. Both
  spellings now work and give identical fits.
- **`rob_linear_test` accepts `lmrob_m` fits, as R does.** R's
  `rob.linear.test` takes `lmrobdetMM` *or* `lmrobM` objects, its own help-page
  example uses `lmrobM`, and so does the book's Example 4.2, which the wrapper's
  type check made impossible to reproduce. Each fit is now also replayed in R
  with the estimator that produced it; refitting an M fit as MM would have
  returned a plausible number for the wrong pair of models.
- **R's integer `NA` no longer arrives as the number `-2147483648`.** R stores
  integer `NA` as `INT_MIN`, and rpy2's pandas conversion maps the column to
  numpy `int32`, which has no missing value, so the sentinel came through as
  ordinary data. Nothing raised and nothing warned; `mean()`, `min()` and
  `dropna()` were simply wrong. Affected columns now become pandas `Int64` with
  real missing values.
- **`cubinf` no longer crashes on an unnamed design matrix.** `names()` on an
  unnamed R vector returns `NULL`, which rpy2 hands back as a `NULLType`, not
  `None`, and not sized, so the length check raised `TypeError`. This was the
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
  never run by any workflow, and had accumulated roughly 790 findings, one of
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
  `project_memory/robstattm-py-planning-docs/`, see `docs/RELOCATED.md`. They
  recorded how the package was built rather than how it works, were already
  excluded from the published site, and `docs/research/*.md` had drifted out of
  step with the code.

---

### Added, release engineering (prepared 2026-08-10)

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
  terminating the Python process, which is what loading it would otherwise do.
- When no R is found, the error lists every location searched and why each was
  rejected.

**A command-line interface**, `robstattm-py` (also `python -m robstattm_py.cli`):

- `setup`, install a private R
- `doctor`, diagnose Python, rpy2, R and the R packages; `--json` for scripting
- `info`, show paths and settings; never starts R, always exits 0
- `install-r-packages`, install R packages without an R console
- `uninstall`, remove what was installed, never anything else

Documented exit codes, and every error carries a concrete remedy.

**Documentation** for people who are not already fluent in both languages:

- *Install in 10 minutes*, assumes no terminal, Python or R experience
- *Coming from R*, the complete R-to-Python translation
- *Platform support*, what works where, including what does not
- *Checking your install*, verifying things, and reading errors
- *Troubleshooting*, symptom-by-symptom fixes

### Fixed, release engineering

- `cov_rob`, `cov_rob_rocke` and `kurt_sd_new` failed when called first in a
  session. RobStatTM's `KurtSDNew.R:42` reads `.Random.seed` unconditionally,
  and R does not create it until the RNG is used; an embedded rpy2 session is
  pristine. R's RNG is now initialised at startup with `set.seed(NULL)`, which
  leaves results random. *(Upstream issue; to be reported.)*
- Importing rpy2 against an R with no shell crashed with `IndexError`.
  rpy2 indexes empty `R CMD config` output and guards only
  `CalledProcessError`. This bit exactly the users who had both a provisioned
  and a system R. Translated to the error rpy2 already handles.
- `check_setup()` reported `rpy2: unknown` on every current install, rpy2 3.6
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

### Changed, release engineering

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
  works afterwards, Apple Silicon provisioning is verified in CI. See
  *Platform support*.
- `pense` and `GSE` are not on conda-forge and are not installed by `setup`;
  use `robstattm-py install-r-packages pense GSE`.
- `robcbi` is archived on CRAN, so the `cubinf` wrapper cannot be exercised
  without building it from the CRAN archive.

[Unreleased]: https://github.com/Aakarsh751/robstattm-py/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Aakarsh751/robstattm-py/releases/tag/v0.1.0
