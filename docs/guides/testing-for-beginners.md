# Checking your install, and reading errors

Two separate questions, often confused:

- **"Is my setup working?"** → `robstattm-py doctor`
- **"Is the package itself correct?"** → the test suite

Most of the time you want the first. The second matters if you are contributing,
or if you want to satisfy yourself that the numbers are right.

---

## Is my setup working?

```bash
robstattm-py doctor
```

The last line is the answer: **`Result: READY`** or **`Result: NOT READY`**.

If it is NOT READY, the `Problems` section lists what is wrong and the command
that fixes each one. You do not have to interpret anything.

> `robstattm-py: command not found`? Use `python -m robstattm_py.cli doctor` —
> identical, and always available. On Windows `pip` frequently installs commands
> to a folder outside your `PATH`.

### The one-line check

From inside Python or a notebook:

```python
import robstattm_py as rpm
rpm.check_setup()
```

Returns `True` when everything required is present.

### Does it actually compute the right answer?

```python
import robstattm_py as rpm

fit = rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral())
print(fit.coefficients)
```

You should get:

```text
[1.52012174e+01 1.25614958e-02]
```

Those exact digits. This dataset and model are deterministic, so any difference
means something is wrong — and is worth reporting.

---

## Is the package correct?

The suite checks every wrapper field by field against a direct R call at
**zero tolerance** (`atol=0, rtol=0`): not "close enough", but the same
floating-point numbers. That is the whole basis for trusting these results, so
it is worth knowing how to run it.

You need the source, not just the installed package:

```bash
git clone https://github.com/Aakarsh751/robstattm-py
cd robstattm-py
pip install -e ".[dev]"
```

Then:

```bash
# fast: skips the notebooks (~4 minutes)
RPM_SKIP_NOTEBOOKS=1 python -m pytest tests/ -q

# everything, including executing all 18 notebooks (~20 minutes)
python -m pytest tests/ -q
```

On Windows PowerShell, set the variable first:

```powershell
$env:RPM_SKIP_NOTEBOOKS = "1"
python -m pytest tests/ -q
```

### The fast subset with no R at all

Roughly 220 tests cover R discovery, the CLI and the plotting backends without
starting R. They run in seconds and are a good sanity check:

```bash
python -m pytest tests/renv/ tests/plot/ -q
```

---

## Reading pytest output

```text
........................................F...............                 [ 45%]
```

Each character is one test: `.` passed, `F` failed, `s` skipped, `E` errored
during setup.

The summary at the bottom is what matters:

```text
934 passed, 19 skipped in 222.83s
```

### Skips are usually fine

`s` means a test decided it could not run — nearly always a missing *optional* R
package. The reason is printed:

```text
SKIPPED [7] tests/external/test_cubinf.py: external R package 'robcbi' not installed
```

That is expected: `robcbi` is archived on CRAN. Skips are not failures.

### Reading a failure

```text
_______________________ test_lmrobdet_mm_matches_r _______________________

    def test_lmrobdet_mm_matches_r(R):
        fit = rpm.lmrobdet_mm("zinc ~ copper", data=mineral)
>       assert_array_equal(fit.coefficients, r_coefficients)
E       AssertionError: arrays differ at index 1

tests/regression/test_lmrobdet_mm.py:88: AssertionError
```

Read it bottom-up:

1. **Last line** — the file and line number.
2. **`E` lines** — what actually went wrong.
3. **`>` line** — the assertion that failed.
4. **Top** — which test.

Useful flags:

```bash
python -m pytest tests/ -q -x           # stop at the first failure
python -m pytest tests/regression -q    # just one area
python -m pytest tests/ -k lmrobdet     # tests matching a name
python -m pytest tests/... --tb=long    # more context on a failure
```

### If many tests fail at once

Almost always a setup problem, not a code problem. Run `robstattm-py doctor`
first — a missing R package fails everything that touches it.

---

## Reading an error from the package itself

Errors from RobStatTM-Py are written to be acted on. They have three parts:

```text
robstattm-py: No usable R installation was found.      <- what happened

Locations checked:                                     <- the evidence
  [skip] env:R_HOME             C:\Old\R\R-4.1.0
         does not look like an R installation.
  [skip] conda:sys.prefix       C:\Python312\lib\R
         Not a directory
  ...

What to do:                                            <- the fix
  Run `robstattm-py setup` to download a private R (about 400 MB), or
  install R yourself and set R_HOME.
```

The middle section is the useful one when something is subtly wrong: it often
shows that R *was* found somewhere and rejected for a specific reason, which is
a much better starting point than "not found".

### R's own errors

Errors from inside R keep R's message and traceback:

```text
robstattm_py._errors.RobStatTMRError: Error in lmrobdetMM(...) :
  'x' must be numeric

R traceback:
  ...
```

These are statistical or data problems, not installation problems. The message
is R's own.

### Warnings

R warnings appear as Python warnings and do not stop anything:

```text
RobStatTMWarning: algorithm did not converge in 50 iterations
```

Worth reading — that one means the estimate may be unreliable — but the code
continues. To collect them:

```python
import warnings

import robstattm_py as rpm
from robstattm_py import RobStatTMWarning

mineral = rpm.datasets.mineral()

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    fit = rpm.lmrob_m("zinc ~ copper", data=mineral)

for w in caught:
    if issubclass(w.category, RobStatTMWarning):
        print(w.message)
```

---

## Reporting a problem

Include this — it captures Python, rpy2, R, the full search trace and every
installed R package version in one go:

```bash
robstattm-py doctor --json
```

Then open an issue at
<https://github.com/Aakarsh751/robstattm-py/issues>.

## See also

- [Troubleshooting](troubleshooting.md) — symptom-by-symptom fixes.
- [Install in 10 minutes](install-beginner.md) — the setup walkthrough.
