# Troubleshooting

If anything is not working, run this first:

```bash
robstattm-py doctor
```

It checks every layer the package depends on — Python, rpy2, R, and the R
packages — and prints what is wrong along with the command that fixes it.

> **Can't run `robstattm-py`?** On Windows, `pip` often installs command-line
> tools into a folder that is not on your `PATH`. Use this instead — it always
> works, and does exactly the same thing:
>
> ```bash
> python -m robstattm_py.cli doctor
> ```

---

## Reading the doctor report

```text
robstattm-py doctor
===================

Python
  version        3.12.4 (x86_64)
  executable     C:\Python312\python.exe
  virtualenv     no
  platform       win-64
  robstattm-py   0.1.0

rpy2
  version        3.6.6
  binding        API

R
  home           C:\Program Files\R\R-4.5.2
  version        R version 4.5.2 (2025-10-31 ucrt)
  architecture   x86_64
  found via      path:R

R packages
  required:
    ✓ RobStatTM        1.0.11
    ✓ robustbase       0.99.7
    ✓ rrcov            1.7.7
    ✓ pyinit           1.1.5

Result: READY
```

The line that matters most when something is wrong is **`found via`** — it names
which of the search locations R was found in. The full list is under
`Where we looked`, which is printed automatically when no R is found, and with
`-v` otherwise.

---

## Where the package looks for R

You do **not** normally need to configure anything. On startup the package
searches these locations in order and uses the first R that works:

| # | Location | Notes |
|---|---|---|
| 1 | `ROBSTATTM_R_HOME` | An R you name explicitly. If it is invalid this is an error, never a silent fallback. |
| 2 | The private R | Installed by the package itself, if you have one. |
| 3 | `R_HOME` | The standard R variable. Skipped if it points somewhere stale. |
| 4 | `CONDA_PREFIX` | R inside the active conda environment. |
| 5 | `sys.prefix` | A conda environment you installed into but did not activate. |
| 6 | `PATH` | `R` or `Rscript` on your `PATH`. |
| 7 | Windows registry | Both per-user and machine-wide installs, newest version first. |
| 8 | `C:\Program Files\R\R-*` | Also `%LOCALAPPDATA%\Programs\R` and `C:\R`. |
| 9 | macOS | `/Library/Frameworks/R.framework`, Homebrew. |
| 10 | Linux | `/usr/lib/R`, `/usr/local/lib/R`, `/opt/R/*`. |

A candidate that fails is recorded and the search continues. Nothing is skipped
silently — every rejection appears in the trace with its reason.

---

## Common problems

### "No usable R installation was found"

The error lists every location that was checked. Read that list first: it often
shows R *was* found somewhere but was rejected for a specific reason.

If you genuinely have no R, install it:

- **Windows** — <https://cran.r-project.org/bin/windows/base/>
- **macOS** — <https://cran.r-project.org/bin/macosx/> (match your CPU: arm64 for
  Apple Silicon, x86_64 for Intel)
- **Linux** — `sudo apt-get install r-base r-base-dev`, or
  `sudo dnf install R R-devel`

Then install the R packages:

```bash
robstattm-py install-r-packages RobStatTM pyinit robustbase rrcov
```

### "R at ... is x86_64, but this Python is arm64"

Your R and your Python are built for different CPU architectures. Loading that R
would crash Python outright, so the package refuses to do it.

This is almost always an Apple Silicon Mac running an Intel R (or vice versa).
Check what you have:

```bash
R --version                                     # look for aarch64 / x86_64
python -c "import platform; print(platform.machine())"
```

Reinstall R so it matches your Python.

### Windows: "LoadLibrary failure: The specified module could not be found"

R's DLLs could not be located. The package puts every directory R needs onto the
search path automatically, so if you still see this:

1. Run `robstattm-py doctor` and check the `home` line. It must point at the R
   installation **root** (`C:\Program Files\R\R-4.5.2`), not at a subdirectory
   such as `bin` or `bin\x64`.
2. If you set `R_HOME` yourself, either correct it or remove it entirely and let
   auto-detection do the work.

### "R package 'RobStatTM' is not installed"

R works, but the R packages are missing. The message names the exact package:

```bash
robstattm-py install-r-packages RobStatTM
```

### `pip install` fails with "rpy2 in API mode cannot be built without R"

The full message is:

```text
Error: rpy2 in API mode cannot be built without R in the PATH or R_HOME
defined. Correct this or force ABI mode-only by defining the environment
variable RPY2_CFFI_MODE=ABI
```

This is the chicken-and-egg case on **Linux**: rpy2 ships no Linux wheels, so
pip compiles it, and its default mode wants R at build time — but you were
going to let `robstattm-py setup` install R. Do as the message says:

```bash
RPY2_CFFI_MODE=ABI pip install robstattm-py
robstattm-py setup
```

ABI mode binds to R at run time instead, so it builds with no R present and
then uses whichever R you end up with. Results are identical.

### rpy2 fails to install with `pip` for other reasons

`pip install rpy2` may try to compile against R and fail if R headers or a C
compiler are missing.

- **Linux** — install the toolchain: `sudo apt-get install r-base-dev build-essential`
- **macOS** — `xcode-select --install`
- **Any platform** — rpy2 also ships a pure-Python binding that needs no
  compiler. Force it with:

  ```bash
  export RPY2_CFFI_MODE=ABI      # Windows: set RPY2_CFFI_MODE=ABI
  ```

  It is slightly slower per call but otherwise identical. `doctor` shows which
  binding is in use on the `binding` line.

### "rpy2 was already initialised against R at ..."

Something imported `rpy2` before `robstattm_py` did. rpy2 picks its R when it is
first imported and cannot change afterwards.

Import `robstattm_py` first, or point it at the same R:

```bash
export ROBSTATTM_R_HOME=/the/path/rpy2/reported
```

### Results change between runs

The covariance, PCA, and external estimators use random subsampling. Fix the
seed immediately before the fit:

```python
import robstattm_py as rpm

rpm.set_seed(42)
cov = rpm.cov_rob(rpm.datasets.wine())
```

Regression estimators (`lmrobdet_mm`, `lmrobdet_dcml`, `lmrob_m`) are
deterministic and need no seed.

---

## Environment variables

| Variable | Effect |
|---|---|
| `ROBSTATTM_R_HOME` | Use this exact R; skip auto-detection entirely. |
| `ROBSTATTM_R_MODE` | `auto` (default), `provisioned`, or `system`. |
| `ROBSTATTM_HOME` | Where the package keeps its private R. Set this if your home directory is full, or its path contains characters that upset R. |
| `R_HOME` | The standard R variable; honoured if `ROBSTATTM_R_HOME` is unset. |
| `RPY2_CFFI_MODE` | `ABI` forces rpy2's compiler-free binding. |

`robstattm-py info` prints all of them with their current values, and never
starts R.

---

## Exit codes

Useful when scripting against the CLI:

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Unexpected internal error |
| 2 | Command-line usage error |
| 10 | No usable R found |
| 11 | R found, but required R packages are missing |
| 12 | R and Python architectures differ |
| 13 | Network, proxy, or TLS failure |
| 14 | Not enough disk space, or permission denied |
| 15 | Provisioning the private R failed |
| 16 | Building RobStatTM from source on Apple Silicon failed |
| 17 | Another setup is already running |

`robstattm-py --help` lists the same table.

---

## Still stuck?

Open an issue at
<https://github.com/Aakarsh751/robstattm-py/issues> and include the output of:

```bash
robstattm-py doctor --json
```

That single command captures your Python, rpy2, R, the full search trace, and
every installed R package version — which is almost always enough to diagnose
the problem without any back-and-forth.

## See also

- [Installation & setup](installation.md) — the full cross-OS setup guide.
- [Getting started](../getting-started.md) — your first robust fit.
