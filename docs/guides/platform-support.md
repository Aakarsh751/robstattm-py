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
| **Linux** (ARM64) | Fully supported | Prebuilt, ~4 min | — |
| **macOS Intel** | Fully supported | Prebuilt, ~3 min | — |
| **macOS Apple Silicon** | Fully supported | **Compiles from source, ~10-15 min** | Needs Xcode command line tools |
| Linux ppc64le | Fully supported | Prebuilt | Rarely tested |
| Windows on ARM | Fully supported *if you install R yourself* | **Not available** | No conda-forge R build |
| 32-bit Python | Not supported | Not available | Use 64-bit Python |

"Fully supported" means the entire test suite runs, and every result is checked
against R at zero tolerance.

---

## Apple Silicon (M1, M2, M3, M4)

**Everything works, but the first setup takes longer.**

conda-forge publishes `r-base`, `r-robustbase` and `r-rrcov` for `osx-arm64`,
but **not** `r-robstattm` or `r-pyinit` (verified 2026-08-10). Those two are
therefore compiled from CRAN source during `robstattm-py setup`.

What that means in practice:

- Setup takes roughly **10-15 minutes** instead of 3-6.
- It needs about **1.5 GB extra** for a compiler toolchain.
- You must have Apple's command line tools. If they are missing, setup stops
  immediately and tells you to run:

  ```bash
  xcode-select --install
  ```

  (a ~700 MB download from Apple, one time).

Once built, it is a fully native arm64 R with no emulation and no performance
penalty.

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

**Fully supported, nothing special.** `robstattm-py setup` uses prebuilt
packages, and an R from your distribution is found automatically at
`/usr/lib/R`, `/usr/local/lib/R` or `/opt/R/*`.

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
