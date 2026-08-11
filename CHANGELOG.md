# Changelog

Notable changes to RobStatTM-Py. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] — 2026-08-10

First public release.

### Added

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

### Fixed

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

### Changed

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
