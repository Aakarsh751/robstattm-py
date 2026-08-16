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

### `pip`: "No matching distribution found for robstattm-py"

```text
ERROR: Could not find a version that satisfies the requirement robstattm-py
       (from versions: none)
ERROR: No matching distribution found for robstattm-py
```

Nothing is wrong with your setup. **RobStatTM-Py is not on PyPI yet**, so there
is nothing for `pip` to download by name. Install from the source repository
instead:

```bash
git clone https://github.com/Aakarsh751/robstattm-py.git
pip install ./robstattm-py
```

Everything after this point — `robstattm-py setup`, `doctor`, and the whole API
— behaves identically. If you want the optional extras, name them the same way:
`pip install "./robstattm-py[plots]"`.

> This error is worth distinguishing from a genuine network or proxy failure,
> which mentions a timeout or a connection, and from a Python-version mismatch,
> which says *"Requires-Python"*. "from versions: none" specifically means the
> index has no such project at all.

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

### "rpy2 is installed, but it could not load R"

> **On Colab?** There is a notebook that installs the package, provisions R,
> exercises the whole surface and prints a copy-pasteable report:
> [`colab_smoke_test.ipynb`](https://colab.research.google.com/github/Aakarsh751/robstattm-py/blob/main/notebooks/colab_smoke_test.ipynb).
> Run it and attach its final block to any issue you open.

Typically on Google Colab, Kaggle, a Docker image, or any Linux box where rpy2
arrived prebuilt — from `apt`, from the image, or as part of a notebook
environment — and R came from `robstattm-py setup`.

rpy2 ships two bindings to R. The **compiled** one (`_rinterface_cffi_api`) is
built against the headers of whichever R was present when rpy2 was built; the
**ABI** one resolves symbols at run time and does not care which R it gets. If
rpy2 was built against one R and you point it at another, the compiled binding
fails to load, usually with an undefined symbol or a missing shared library.

Since 0.1.0, when the R came from `robstattm-py setup` the ABI binding is
selected before rpy2 is imported, so the compiled binding is never given a
chance to fail against an R it was not built for. A system R is left on its
faster compiled binding, since that is plausibly the one rpy2 was built against.

**On Google Colab or Kaggle the simplest fix is to use the system R rather than
provision a new one.** `pip` rebuilds rpy2 from source against that R (`/usr/lib/R`)
when it installs, so the compiled binding matches it exactly. Install the R
packages into it and skip `setup` entirely — see the
[Colab / Kaggle quickstart](installation.md#google-colab--kaggle-fastest-path--no-r-download).
Provisioning a separate R is the harder path there and is not needed.

If you hit it anyway — an R that is neither, or an rpy2/R pairing we cannot
predict — set the variable yourself. It must be set **before Python starts**;
rpy2 reads it when it first loads R, and by the time you can run a cell in an
already-started kernel it may be too late:

```bash
export RPY2_CFFI_MODE=ABI
```

In a Colab or Jupyter notebook, put this in the **first** cell, before any
import — and if you have already imported anything that loads R, restart the
runtime first. rpy2 embeds R as a process-global singleton, so the binding
cannot be changed once R is loaded:

```python
import os
os.environ["RPY2_CFFI_MODE"] = "ABI"
```

The alternatives, if you prefer not to use ABI mode:

```bash
pip install --force-reinstall --no-binary rpy2 rpy2   # rebuild against this R
robstattm-py setup --use-system-r                     # use the R rpy2 knows
```

> **If you are told "rpy2 is not installed" while `doctor` also reports an rpy2
> version, that is a bug and it is fixed.** Before 0.1.0, every failure to load
> R was reported as a missing rpy2, because importing `rpy2.robjects` both
> imports a package *and* starts R, and both raise `ImportError`. The message
> now distinguishes them and quotes the real error.

### "cannot import name 'default_converter' from 'rpy2.robjects' (unknown location)"

This is **not** a binding or R-loading problem — `rpy2.robjects` cannot be
imported at all. rpy2 3.6 is split across three separately-versioned
distributions, and when they drift out of step `rpy2.robjects` resolves to an
empty namespace package with no file. `doctor` now names the culprit directly:

```text
rpy2 is installed, but its components are at mismatched versions, so
`rpy2.robjects` could not be imported:
    rpy2             3.6.7
    rpy2-rinterface  3.6.6
    rpy2-robjects    3.6.5
```

Seen most often on **Google Colab and Kaggle**, whose preinstalled rpy2 is
sometimes a mismatched set (a partial `pip` upgrade does the same). Reinstall a
consistent set, then restart the runtime/kernel:

```bash
pip install --force-reinstall --no-cache-dir rpy2
```

> rpy2 embeds R as a process-global singleton, so the restart is required for the
> repaired install to take effect. On Colab this is `Runtime → Restart runtime`.

### Windows: setup reaches "[4/4] Verifying" and then fails

Symptoms — one of:

```text
robstattm-py: The provisioned R could not be started.

Mingw-w64 runtime failure:
32 bit pseudo relocation at 00007FFDF2815D45 out of range, targeting ...
```

```text
The specified module could not be found.        (exit code 3221225781)
```

**Nothing is wrong with the download.** Steps 1–3 copied every file correctly;
step 4 is simply the first moment anything actually starts R, so it is where a
loading problem surfaces.

Windows resolves a DLL by scanning `PATH` from left to right and loading the
first matching *name*. R needs `R.dll`, `Rblas.dll` and a mingw runtime — names
that a CRAN R installation, Rtools, MSYS2, Git's bundled mingw and other conda
environments all also ship. If one of those is found first, the wrong copy is
loaded into R. It then either fails outright (`0xC0000135`) or loads and dies on
the pseudo-relocation message: a relocation that can only reach ±2 GB, asked to
reach further, because the two images came from unrelated builds.

Since 0.1.0 the environment's own directories are placed in front of `PATH`
before R is started, so this should not occur. If you still hit it:

```bash
robstattm-py doctor            # shows which R was found and how
```

Then, in order of preference:

1. **Use the R you already have** — skips the download entirely:
   ```bash
   robstattm-py setup --use-system-r
   ```
2. **Retry from a clean PATH**, in a new PowerShell window:
   ```powershell
   $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
   robstattm-py setup
   ```
3. Pin an R explicitly and skip discovery: set `ROBSTATTM_R_HOME` to its root.

> **`--force` will not help here** and costs several minutes and a gigabyte. It
> re-downloads bytes that were already correct. The problem is on the machine,
> not in the package.

To see exactly which `PATH` arrangement works, from a source checkout:

```bash
python dev/_diagnose_r_startup.py
```

It launches the provisioned R six times varying only `PATH` and reports which
succeed.

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
RPY2_CFFI_MODE=ABI pip install ./robstattm-py
robstattm-py setup
```

> Until RobStatTM-Py is published to PyPI, replace `pip install robstattm-py`
> with `git clone https://github.com/Aakarsh751/robstattm-py.git` followed by
> `pip install ./robstattm-py`. Everything else is unchanged.

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
