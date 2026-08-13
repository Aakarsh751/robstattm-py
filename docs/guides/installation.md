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
> | R | ≥ 4.2 (tested on 4.5.2) | found automatically — registry, `PATH`, conda, and the standard install locations |
> | R packages | `RobStatTM`, `pyinit`, `robustbase`, `rrcov` (core); `pense`, `GSE` (optional) | `library()` search path |
> | Python | ≥ 3.10 | the interpreter you `pip install` into |
> | rpy2 | ≥ 3.6 | installed from PyPI; links against R at import |

If you just want the fast path, jump to [Quick reference](#quick-reference) for
copy-paste commands per OS, then [Verify](#5-verify-everything).

---

## Google Colab / Kaggle (fastest path — no R download)

Colab and Kaggle already ship R and `rpy2`, so you skip steps 1 and 3 entirely
and you do **not** need `robstattm-py setup` (that provisions a private R, which
is only worth it off these platforms). One cell installs the package and the R
packages against the R that is already there:

```text
# Cell 1 — install (about a minute; the R packages compile once)
!pip install -q "git+https://github.com/Aakarsh751/robstattm-py.git"
!python -m robstattm_py.cli install-r-packages RobStatTM pyinit robustbase rrcov
```

```python
# Cell 2 — use it
import robstattm_py as rpm
fit = rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())
print(fit.summary())
```

> **Why this works, and why it beats provisioning here:** `pip` rebuilds `rpy2`
> from source against Colab's own R (`/usr/lib/R`) as it installs, so rpy2's
> compiled binding matches that R exactly — no `RPY2_CFFI_MODE` cell needed.
> Provisioning a *separate* R with `robstattm-py setup` is the harder path on
> these platforms and is not needed; stick with the two cells above and you avoid
> the whole binding-mismatch question.

There is also a full end-to-end
[Colab smoke-test notebook](https://colab.research.google.com/github/Aakarsh751/robstattm-py/blob/main/notebooks/colab_smoke_test.ipynb)
that installs, provisions, fits, and prints a copy-pasteable report.

---

## 1. Install R

### Windows

Download the installer from <https://cran.r-project.org/bin/windows/base/> and
run it. Accept the defaults — there is nothing to note down.

> The Windows installer records R in the registry, and RobStatTM-Py reads it
> from there, so R does **not** need to be on your `PATH` and you do **not**
> need to set `R_HOME`. The package also puts R's own DLL directories on the
> search path for you, which is what prevents the
> `LoadLibrary failure: The specified module could not be found` error.

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

You can do this from your normal terminal after [step 3](#3-install-python-rpy2-and-robstattm-py) —
no R knowledge, and no R console, required:

```bash
robstattm-py install-r-packages RobStatTM pyinit robustbase rrcov

# optional — only for the external "stretch" estimators
# (pense / pense_cv / gse / tsgs):
robstattm-py install-r-packages pense GSE
```

These go into a private library that RobStatTM-Py owns, so your own R
installation is left exactly as it was. This compiles C/Fortran code, so the
first install can take several minutes.

<details>
<summary>Prefer to use R directly?</summary>

Open an R session (`R` in a terminal, or RGui/RStudio) and run:

```r
install.packages(c("RobStatTM", "pyinit", "robustbase", "rrcov"))
install.packages(c("pense", "GSE"))   # optional
```

Pick a CRAN mirror when prompted (any is fine).

**Linux tip:** for much faster *binary* installs (no compilation), use Posit
Public Package Manager:

```r
options(repos = "https://packagemanager.posit.co/cran/latest")
install.packages(c("RobStatTM", "pyinit", "robustbase", "rrcov"))
```

</details>

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

Get the source, then install from the directory that now contains the
`robstattm-py/` folder:

```bash
git clone https://github.com/Aakarsh751/robstattm-py.git
pip install -e robstattm-py/
```

Optional extras:

```bash
pip install -e "robstattm-py/[notebooks]"   # scipy + matplotlib + jupyter, to run the example notebooks
pip install -e "robstattm-py/[dev]"         # the test/lint toolchain
```

> RobStatTM-Py is not yet on PyPI, so install it **editable from the repo**
> (`-e`). `rpy2` *is* on PyPI and installs automatically. On Windows, `rpy2`
> ships as a prebuilt wheel; on macOS/Linux it may build from source, which
> needs R already installed (step 1) and a C compiler.

---

## 4. Point Python at R — nothing to do

RobStatTM-Py locates R by itself, on every OS. It searches, in order:

1. `ROBSTATTM_R_HOME`, if you set it
2. R installed by `robstattm-py setup`
3. `R_HOME`
4. The active conda environment
5. `R` or `Rscript` on your `PATH`
6. **Windows:** the registry (per-user *and* machine-wide installs, newest
   first), then `C:\Program Files\R\R-*`
7. **macOS:** `/Library/Frameworks/R.framework`, Homebrew
8. **Linux:** `/usr/lib/R`, `/usr/local/lib/R`, `/opt/R/*`

So on any platform, this is all you need:

```python
import robstattm_py as rpm
```

An R built for a different CPU architecture is rejected *before* it can crash
Python, and if the search comes up empty the error lists every location that was
checked and why each was ruled out.

> **Setting `R_HOME` yourself still works** and takes priority over
> auto-detection — useful when you have several R versions installed. Prefer
> `ROBSTATTM_R_HOME`, which pins R for this package only and leaves your other R
> tooling alone.

To see which R was chosen:

```bash
robstattm-py doctor
```

If that command is not found — common on Windows, where `pip` often installs
scripts to a folder outside your `PATH` — use this instead, which always works:

```bash
python -m robstattm_py.cli doctor
```

---

## 5. Verify everything

```python
import robstattm_py as rpm
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
pip install -e "robstattm-py/[notebooks]"   # installs ipykernel + plotting deps
python -m ipykernel install --user --name robstattm-py
```

No R configuration cell is needed — notebooks just `import robstattm_py as rpm`
like any other script.

---

## 7. Troubleshooting

Run this first; it diagnoses every layer and prints the fix for whatever is
wrong:

```bash
robstattm-py doctor
```

The [troubleshooting guide](troubleshooting.md) covers each failure in depth.
The most common ones:

| Symptom | Cause & fix |
|---|---|
| `robstattm-py: command not found` | `pip` installed the script outside your `PATH` (usual on Windows). Use `python -m robstattm_py.cli doctor` instead. |
| `RobStatTMSetupError: rpy2 is not installed` | `pip install "rpy2>=3.6"` (it's a dependency, so normally automatic). |
| `No usable R installation was found` | The message lists every location searched. Install R (step 1), or set `ROBSTATTM_R_HOME` to an existing install. |
| **Windows:** `LoadLibrary failure: The specified module could not be found` | Run `robstattm-py doctor` and check the `home` line points at the install **root** (`C:\Program Files\R\R-4.5.2`), not `bin\x64`. If you set `R_HOME` by hand, try removing it and letting auto-detection work. |
| `R at ... is x86_64, but this Python is arm64` | Your R and Python target different CPUs. Reinstall R to match `platform.machine()`. |
| `R package 'RobStatTM' is not installed` | `robstattm-py install-r-packages RobStatTM`. The message names exactly which package is missing. |
| rpy2 fails to build (`R.h: No such file`) on Linux | Install R headers + toolchain: `apt-get install r-base-dev build-essential` (or `dnf install R-devel gcc-gfortran`). Or set `RPY2_CFFI_MODE=ABI` to use rpy2's compiler-free binding. |
| `R package 'pense'/'GSE' is not installed` | Only needed for `pense`/`gse`/`tsgs`: `robstattm-py install-r-packages pense GSE`. |
| `RobStatTMRError: … (quasi-)separable …` from `*_logreg` | Not a setup issue — the binary response is perfectly separable. Condition the data or drop over-powerful predictors. |
| Conda picks the wrong R | Set `ROBSTATTM_R_MODE=system`, or `ROBSTATTM_R_HOME` to the R you intend to use. |
| Results aren't reproducible across runs | The covariance/PCA/external estimators use random subsampling — call `rpm.set_seed(n)` immediately before the fit. (Regression estimators are deterministic.) |

Still stuck? Open an issue with the output of `robstattm-py doctor --json` — it
captures your Python, rpy2, R, the full search trace, and every R package
version in one go.

---

## Quick reference

**Windows (PowerShell):**

```powershell
# 1. install R from CRAN (accept the defaults; no need to note the path)
py -3 -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e robstattm-py/
python -m robstattm_py.cli install-r-packages RobStatTM pyinit robustbase rrcov
python -m robstattm_py.cli doctor
```

**macOS / Linux (bash):**

```bash
# Linux: sudo apt-get install -y r-base r-base-dev   (or dnf install R R-devel)
# macOS: install R .pkg matching your CPU arch
python3 -m venv .venv && source .venv/bin/activate
pip install -e robstattm-py/
robstattm-py install-r-packages RobStatTM pyinit robustbase rrcov
robstattm-py doctor
```

No `R_HOME` in either — the package finds R on its own.

## See also

- [Getting started](../getting-started.md) — your first robust fit.
- [External estimators](external.md) — installing `pense` / `GSE`.
- `rpm.check_setup()` — the built-in environment diagnostic.
