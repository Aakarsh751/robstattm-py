# Platform support

What works where, stated plainly — including the places where it does not.

Two things can vary by platform: whether RobStatTM-Py can **install R for you**,
and whether the **wrappers** work once R is present. The second is the same
everywhere. Only the first differs.

---

## Summary

| Platform | Wrappers | `robstattm-py setup` | Notes |
|---|---|---|---|
| **Windows** (64-bit) | Fully supported | Prebuilt, ~4 min | Use a short install path; see below |
| **Linux** (x86-64) | Fully supported | Prebuilt, ~3 min | — |
| **Linux** (ARM64) | Fully supported | **Compiles from source, ~10-15 min** | Same conda-forge gap as Apple Silicon |
| **macOS Intel** | Fully supported | Prebuilt, ~3 min | — |
| **macOS Apple Silicon** | Fully supported | **Compiles from source, ~10-15 min** | Needs Xcode command line tools; verified in CI |
| Linux ppc64le | Fully supported | **Compiles from source** | Same gap; rarely tested |
| Windows on ARM | Fully supported *if you install R yourself* | **Not available** | No conda-forge R build |
| 32-bit Python | Not supported | Not available | Use 64-bit Python |

"Fully supported" means the entire test suite runs, and every result is checked
against R at zero tolerance.

---

## Platforms that compile RobStatTM from source

**Apple Silicon (M1-M4), ARM Linux, and POWER Linux.**

Everything works on these, but the first setup takes longer.

conda-forge publishes `r-base`, `r-robustbase`, `r-rrcov` and `r-robust` for
all of them, but **not** `r-robstattm` or `r-pyinit` — those exist only for
`linux-64`, `osx-64` and `win-64` (verified 2026-08-11). They are therefore
compiled from CRAN source during `robstattm-py setup`.

Apple Silicon is the case people notice, but ARM Linux (Raspberry Pi, AWS
Graviton) and POWER have exactly the same gap.

What that means in practice:

- Setup takes roughly **10-15 minutes** instead of 3-6.
- It needs about **1.5 GB extra** for a compiler toolchain.
- On macOS you must have Apple's command line tools. If they are missing,
  setup stops immediately and tells you to run:

  ```bash
  xcode-select --install
  ```

  (a ~700 MB download from Apple, one time).

Once built, it is a fully native arm64 R with no emulation and no performance
penalty.

> **Where it gets installed.** On macOS the private R goes in
> `~/.robstattm-py`, not the usual `~/Library/Application Support`. R's own
> launcher script cannot cope with the space in "Application Support" — it
> expands its path unquoted and fails to start. Any path you choose with
> `ROBSTATTM_HOME` must likewise contain no spaces; `setup` checks this
> before downloading anything.

### If the source build fails

It is the most fragile path in the package, and it says so rather than pretending
otherwise. Two alternatives, in order of preference:

1. **Use an R you install yourself.** CRAN publishes native arm64 builds of both
   R and RobStatTM, so this avoids compiling anything:

   ```bash
   # install R from https://cran.r-project.org/bin/macosx/ (pick the arm64 build)
   robstattm-py install-r-packages RobStatTM pyinit robustbase rrcov
   robstattm-py doctor
   ```

   No further configuration — RobStatTM-Py finds it automatically.

2. **Point at an existing R** you already have:

   ```bash
   robstattm-py setup --use-system-r
   ```

### Getting this fixed properly

The real fix is upstream: adding `osx-arm64` to the `r-robstattm` and `r-pyinit`
conda-forge feedstocks. Every dependency already has an arm64 build, so this is
likely just a rerender. When it lands, Apple Silicon becomes as fast and simple
as every other platform and this section shrinks to nothing.

---

## Windows

**Fully supported, with one thing to know about paths.**

conda-forge's Windows R depends on a mingw headers package whose files sit about
215 characters deep inside the download cache. Windows refuses paths longer than
260 characters unless long-path support is enabled (it is off by default and
turning it on needs administrator rights).

RobStatTM-Py checks this **before** downloading anything and stops with the exact
fix if your install path is too long. If you hit it:

```powershell
$env:ROBSTATTM_HOME = 'C:\rtm'
robstattm-py setup

# to make it permanent:
setx ROBSTATTM_HOME C:\rtm
```

Two smaller Windows notes:

- `pip` often installs commands to a folder outside your `PATH`, so
  `robstattm-py` may be "not found". `python -m robstattm_py.cli` always works
  and is identical.
- R does **not** need to be on your `PATH`. RobStatTM-Py reads the Windows
  registry, which the CRAN installer writes to, so a default install is found
  with no configuration.

---

## Linux

**Fully supported**, with one wrinkle at install time if you do not already
have R.

`rpy2` — the bridge this package is built on — publishes prebuilt wheels for
Windows and macOS but **not for Linux**, so on Linux `pip` compiles it. Its
default build mode refuses to compile unless R is already present, which is a
chicken-and-egg problem if you were relying on `robstattm-py setup` to install
R for you. The fix is one environment variable:

```bash
RPY2_CFFI_MODE=ABI pip install ./robstattm-py
robstattm-py setup
```

> Until RobStatTM-Py is published to PyPI, replace `pip install robstattm-py`
> with `git clone https://github.com/Aakarsh751/robstattm-py.git` followed by
> `pip install ./robstattm-py`. Everything else is unchanged.

ABI mode resolves R's symbols at run time instead of link time, so it builds
with no R present and then binds to whichever R `setup` installs. Per-call
overhead is marginally higher; results are identical. `robstattm-py doctor`
shows which mode is in use on the `binding` line.

If you already have R installed, a plain install works and you get the faster
API mode.

Once installed, `robstattm-py setup` uses prebuilt packages, and an R from your
distribution is found automatically at `/usr/lib/R`, `/usr/local/lib/R` or
`/opt/R/*`.

If you install R packages from source rather than using `setup`, you need the R
headers and a toolchain:

```bash
sudo apt-get install r-base-dev build-essential gfortran   # Debian/Ubuntu
sudo dnf install R-devel gcc-gfortran                      # Fedora/RHEL
```

---

## Optional estimators

The `pense`, `gse` and `tsgs` wrappers need R packages that conda-forge does not
carry, so they are **not** installed by `robstattm-py setup`. Install them
separately when you want them:

```bash
robstattm-py install-r-packages pense GSE
```

These compile heavy C++ and can fail on a machine without a full toolchain. They
are optional by design: everything else keeps working without them, and
`doctor` reports them as optional rather than missing.

`robcbi` is **archived on CRAN** (since 2024-05-27) and cannot be installed
normally at all. The `cubinf` wrapper exists but will skip unless you build
`robcbi` from the CRAN archive yourself.

See [External estimators](external.md) for the full picture.

---

## Python versions

Supported: **3.10, 3.11, 3.12, 3.13**. Tested in CI on 3.10, 3.11 and 3.12
across Linux, Windows and macOS.

Your Python must be **64-bit**, and on macOS its architecture must match R's.
A mismatch is detected and refused with a clear message rather than crashing the
interpreter — which is what would otherwise happen.

---

## How these claims are checked

Not by assertion:

- Every push runs the full suite on Linux, Windows and macOS with a system R,
  and asserts that R was found by **auto-detection**, not by configuration.
- A nightly job provisions R on machines with **none** — a bare
  `python:3.12-slim` container, plus Windows and both macOS architectures with
  the preinstalled R removed and the job failing if any trace remains. It then
  asserts the provisioned R is the one in use and runs a real fit against pinned
  coefficients.
- A per-pull-request job asks conda's solver whether the package set is
  satisfiable on all five platforms, which is how the Apple Silicon gap above
  stays accurate.

If something in the table is wrong, please
[open an issue](https://github.com/Aakarsh751/robstattm-py/issues) with the
output of `robstattm-py doctor --json`.
