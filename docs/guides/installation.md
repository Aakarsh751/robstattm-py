# Installation & setup (Windows · macOS · Linux)

RobStatTM-Py is a **bridge to R**: it calls the original RobStatTM routines
through [`rpy2`](https://rpy2.github.io/). So a working setup has four layers,
installed in this order:

1. **R** (the language) — 4.2 or newer.
2. **The R packages** — `RobStatTM` + its dependencies (and, optionally, the
   stretch packages `pense` / `GSE`).
3. **Python** — 3.10 or newer, ideally in a virtual environment.
4. **`rpy2` + RobStatTM-Py** — the Python side, which finds and drives R.

> **At a glance**
>
> | Layer | Requirement | How RobStatTM-Py finds it |
> |---|---|---|
> | R | ≥ 4.2 (tested on 4.5.2) | `R_HOME` env var, or `R` on your `PATH` |
> | R packages | `RobStatTM`, `pyinit`, `robustbase`, `rrcov` (core); `pense`, `GSE` (optional) | `library()` search path |
> | Python | ≥ 3.10 | the interpreter you `pip install` into |
> | rpy2 | ≥ 3.6 | installed from PyPI; links against R at import |

If you just want the fast path, jump to [Quick reference](#quick-reference) for
copy-paste commands per OS, then [Verify](#5-verify-everything).

---

## 1. Install R

### Windows

1. Download the installer from <https://cran.r-project.org/bin/windows/base/>
   and run it. Accept the defaults.
2. Note the install path — it looks like `C:\Program Files\R\R-4.5.2`. You will
   point Python at it in [step 4](#4-point-python-at-r-r_home).

> On 64-bit Windows the R DLLs live in `…\R-4.5.2\bin\x64`. RobStatTM-Py adds
> this to the DLL search path for you (see `_ensure_windows_r_dll_path`), so you
> normally only need to set `R_HOME`.

### macOS

- **Recommended:** download the `.pkg` from
  <https://cran.r-project.org/bin/macosx/> — pick the **arm64** build on Apple
  Silicon (M1/M2/M3) or the **x86_64** build on Intel. Installing the wrong
  architecture is the #1 cause of `rpy2` import failures on Mac.
- **Or via Homebrew:** `brew install r`.

After installing, confirm the architecture matches your Python:

```bash
R --version            # shows "aarch64" (Apple Silicon) or "x86_64" (Intel)
python3 -c "import platform; print(platform.machine())"   # must match
```

### Linux

**Debian / Ubuntu:**

```bash
sudo apt-get update
sudo apt-get install -y r-base r-base-dev   # r-base-dev provides headers for building R packages
```

**Fedora / RHEL / CentOS:**

```bash
sudo dnf install -y R R-devel
```

> `*-dev` / `*-devel` is important: building `RobStatTM` (and `rpy2`) from
> source needs R's headers and a C/C++/Fortran toolchain
> (`build-essential` / `gcc-gfortran`).

---

## 2. Install the R packages

Open an **R session** (`R` in a terminal, or RGui/RStudio) and run:

```r
install.packages(c("RobStatTM", "pyinit", "robustbase", "rrcov"))

# optional — only needed for the external "stretch" estimators
# (pense / pense_cv / gse / tsgs):
install.packages(c("pense", "GSE"))
```

Pick a CRAN mirror when prompted (any is fine). This compiles C/Fortran code, so
the first install can take several minutes.

> **Linux tip:** for much faster *binary* installs (no compilation), use Posit
> Public Package Manager:
> ```r
> options(repos = "https://packagemanager.posit.co/cran/latest")
> install.packages(c("RobStatTM", "pyinit", "robustbase", "rrcov"))
> ```

---

## 3. Install Python, rpy2, and RobStatTM-Py

Use a **virtual environment** so the R bridge is isolated from system Python.

### Create and activate a venv

```bash
# Windows (PowerShell)
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### Install the package (which pulls in rpy2, numpy, pandas)

From the directory that contains the `robstatm-py/` folder:

```bash
pip install -e robstatm-py/
```

Optional extras:

```bash
pip install -e "robstatm-py/[notebooks]"   # scipy + matplotlib + jupyter, to run the example notebooks
pip install -e "robstatm-py/[dev]"         # the test/lint toolchain
```

> RobStatTM-Py is not yet on PyPI, so install it **editable from the repo**
> (`-e`). `rpy2` *is* on PyPI and installs automatically. On Windows, `rpy2`
> ships as a prebuilt wheel; on macOS/Linux it may build from source, which
> needs R already installed (step 1) and a C compiler.

---

## 4. Point Python at R (`R_HOME`)

`rpy2` has to locate your R installation. How depends on the OS:

### Windows — set `R_HOME` before importing

Windows does not expose R on the default `PATH`, so set it explicitly **before**
`import robstatm_py` (adjust the version to match yours):

```python
import os
os.environ["R_HOME"] = r"C:\Program Files\R\R-4.5.2"

import robstatm_py as rpm   # the package handles the bin\x64 DLL path for you
```

To avoid repeating this, set it once as a system environment variable
(System Properties → Environment Variables → New → `R_HOME` =
`C:\Program Files\R\R-4.5.2`) and restart your shell.

### macOS / Linux — usually automatic

If `R` is on your `PATH`, `rpy2` finds it with no configuration. If you have
multiple R installs (or use a non-standard prefix), pin it:

```bash
export R_HOME="$(R RHOME)"     # add to ~/.bashrc / ~/.zshrc to persist
```

---

## 5. Verify everything

```python
import robstatm_py as rpm
rpm.check_setup()
```

You should see a checklist marking R, `rpy2`, and each R package `READY`:

```text
RobStatTM-Py setup check
========================
Python:       3.11.x
rpy2:         3.6.x
R:            R version 4.5.2 ...
  RobStatTM     1.0.11                  [OK]
  robustbase    0.99-x                  [OK]
  rrcov         1.7-x                   [OK]
  pyinit        1.1.x                   [OK]
  pense         (not installed)         [WARN]   ← optional
  GSE           (not installed)         [WARN]   ← optional
Result: READY for core wrappers ...
```

`check_setup()` returns `True` when all *core* packages are present. Then run
your first fit:

```python
fit = rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())
print(fit.summary())
```

---

## 6. Jupyter (optional)

To run notebooks or use the rich `_repr_html_` result rendering:

```bash
pip install -e "robstatm-py/[notebooks]"   # installs ipykernel + plotting deps
python -m ipykernel install --user --name robstatm-py
```

On Windows, put the `R_HOME` bootstrap from [step 4](#windows--set-r_home-before-importing)
in the **first cell** of each notebook (the bundled notebooks already do this).

---

## 7. Troubleshooting

| Symptom | Cause & fix |
|---|---|
| `RobStatTMSetupError: rpy2 is not installed` | `pip install "rpy2>=3.6"` (it's a dependency, so normally automatic). |
| rpy2 can't find R / `R_HOME` errors at import | Set `R_HOME` (step 4). On macOS/Linux, `export R_HOME="$(R RHOME)"`; confirm `R` runs in your terminal. |
| **Windows:** `LoadLibrary failure: The specified module could not be found` | R's `bin\x64` isn't on the DLL path. RobStatTM-Py adds it automatically — make sure `R_HOME` points at the install **root** (e.g. `C:\Program Files\R\R-4.5.2`), not `bin\x64`. |
| `RobStatTMSetupError: R package 'RobStatTM' is not installed` | Run step 2 in R: `install.packages("RobStatTM")`. The message names exactly which package is missing. |
| **macOS:** `mach-o, but wrong architecture` / rpy2 import crash | Your R and Python architectures differ. Reinstall R matching `platform.machine()` (arm64 vs x86_64). |
| rpy2 fails to build (`R.h: No such file`) on Linux | Install R headers + toolchain: `apt-get install r-base-dev build-essential` (or `dnf install R-devel gcc-gfortran`). |
| `RobStatTMSetupError: R package 'pense'/'GSE' is not installed` | Only needed for `pense`/`gse`/`tsgs`. Install them (step 2) or avoid those functions. |
| `RobStatTMRError: … (quasi-)separable …` from `*_logreg` | Not a setup issue — the binary response is perfectly separable. Condition the data or drop over-powerful predictors. |
| Conda environments pick the wrong R | Conda may ship its own `r-base`. Either install RobStatTM into the conda R, or set `R_HOME` to the R you intend to use. |
| Results aren't reproducible across runs | The covariance/PCA/external estimators use random subsampling — call `rpm.set_seed(n)` immediately before the fit. (Regression estimators are deterministic.) |

If `check_setup()` still reports a problem, run it with the full report and
share the output — it pinpoints which of the four layers is missing.

---

## Quick reference

**Windows (PowerShell):**

```powershell
# 1. install R from CRAN, note the path
# 2. in R:  install.packages(c("RobStatTM","pyinit","robustbase","rrcov"))
py -3 -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e robstatm-py/
$env:R_HOME = "C:\Program Files\R\R-4.5.2"
python -c "import robstatm_py as rpm; rpm.check_setup()"
```

**macOS / Linux (bash):**

```bash
# Linux: sudo apt-get install -y r-base r-base-dev   (or dnf install R R-devel)
# macOS: install R .pkg matching your CPU arch
Rscript -e 'install.packages(c("RobStatTM","pyinit","robustbase","rrcov"), repos="https://cloud.r-project.org")'
python3 -m venv .venv && source .venv/bin/activate
pip install -e robstatm-py/
export R_HOME="$(R RHOME)"
python -c "import robstatm_py as rpm; rpm.check_setup()"
```

## See also

- [Getting started](../getting-started.md) — your first robust fit.
- [External estimators](external.md) — installing `pense` / `GSE`.
- `rpm.check_setup()` — the built-in environment diagnostic.
