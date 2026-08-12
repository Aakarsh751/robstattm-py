# Install in 10 minutes (no R knowledge needed)

This guide assumes nothing. If you have never opened a terminal, never used R,
and are not sure what "pip" is, you are in the right place.

By the end you will have run a robust regression on real data.

> **Already comfortable with Python and R?** The
> [standard installation guide](installation.md) is shorter.

---

## What you are installing, and why there are two parts

RobStatTM-Py is a Python package that runs statistical methods originally
written in **R**, a different programming language. It does this so the numbers
you get are exactly the ones the textbook authors produced — nothing is
reimplemented and no results are approximated.

That means two things have to be on your computer:

| Part | What it is | How you get it |
|---|---|---|
| **Python** + RobStatTM-Py | What you write your code in | `pip`, below |
| **R** + RobStatTM | Does the actual calculation, behind the scenes | one command, below |

**You never have to learn R or open it.** You just need it installed, and one
command does that for you.

---

## Step 1 — Open a terminal

A terminal is a window where you type commands instead of clicking.

- **Windows** — press the Start button, type `powershell`, press Enter.
- **macOS** — press `Cmd + Space`, type `terminal`, press Enter.
- **Linux** — press `Ctrl + Alt + T`.

You will see a window with a blinking cursor. Everything below gets typed there,
one line at a time, pressing Enter after each.

---

## Step 2 — Check you have Python

Type this and press Enter:

```bash
python --version
```

You should see something like `Python 3.12.4`. Any version **3.10 or higher** is
fine.

<details>
<summary>If that printed an error, or a version below 3.10</summary>

Install Python from <https://www.python.org/downloads/>. Download the installer,
run it, and — **this part matters on Windows** — tick the box that says
**"Add python.exe to PATH"** on the first screen before clicking Install.

Then close the terminal, open a new one, and try `python --version` again.

On macOS you may need to type `python3` instead of `python` everywhere in this
guide.

</details>

---

## Step 3 — Make a project folder and a virtual environment

A *virtual environment* is a private, self-contained copy of Python for one
project. It keeps this project's packages from interfering with anything else on
your computer. It is one command, and it is worth it.

**Windows (PowerShell):**

```powershell
mkdir robust-stats
cd robust-stats
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
mkdir robust-stats
cd robust-stats
python3 -m venv .venv
source .venv/bin/activate
```

Your prompt should now start with `(.venv)`. That tells you the environment is
active.

> **Windows: "running scripts is disabled on this system"?** Run this once, then
> try the activate line again:
>
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```
>
> This permits locally-created scripts; it is the standard fix and does not
> weaken anything else.

> You must activate the environment **every time** you come back to this project
> — just the last line above.

---

## Step 4 — Install RobStatTM-Py

> **Not yet on PyPI.** RobStatTM-Py has not been published to the Python Package
> Index yet, so `pip install robstattm-py` will fail with *"No matching
> distribution found"*. Install from the source repository instead — the two
> commands below. Everything after this step is identical either way.

You need `git` for this. If `git --version` prints an error, install it from
<https://git-scm.com/downloads> first (accept every default), then close and
reopen your terminal.

```bash
git clone https://github.com/Aakarsh751/robstattm-py.git
pip install ./robstattm-py
```

This takes a minute or two and prints a lot of text. The last line should say
`Successfully installed ...`.

Check it worked:

```bash
python -c "import robstattm_py; print(robstattm_py.__version__)"
```

That should print a version number such as `0.1.0`. It is fine that R is not
installed yet — importing the package does not start R.

> **On Linux, and you do not have R yet?** Use this instead for the second
> command:
>
> ```bash
> RPY2_CFFI_MODE=ABI pip install ./robstattm-py
> ```
>
> One of the pieces underneath (`rpy2`) publishes ready-made packages for
> Windows and macOS but not for Linux, so on Linux it gets compiled — and by
> default it refuses to compile unless R is already there. `RPY2_CFFI_MODE=ABI`
> tells it to connect to R when it *runs* rather than when it is built, which
> is what you want here. Everything works the same afterwards.
>
> Already have R installed? Then the plain `pip install` above is fine.

---

## Step 5 — Install R

You do not need to download R yourself. Run:

```bash
robstattm-py setup
```

It will tell you what it is about to download and ask you to confirm. Type `y`
and press Enter.

This takes **3 to 6 minutes** and downloads about **400 MB**. It needs roughly
**4 GB of free disk space** on Windows while it works.

You will see progress like:

```text
[1/4] Getting the package manager (micromamba)
[2/4] Installing R and RobStatTM from conda-forge
      roughly 400 MB to download; this usually takes 3-6 minutes
[3/4] No source build needed on this platform
[4/4] Verifying

R 4.5.3 is ready at .../envs/r/lib/R
```

> **`robstattm-py: command not found`?** This is common on Windows: `pip` puts
> commands in a folder your terminal does not look in. Use this instead — it
> always works, and does exactly the same thing:
>
> ```bash
> python -m robstattm_py.cli setup
> ```
>
> The same substitution works for every `robstattm-py ...` command in these
> guides.

> **Already have R installed?** You can skip this step entirely — RobStatTM-Py
> finds an existing R automatically. Run `robstattm-py doctor` to check, and if
> it reports missing R packages run
> `robstattm-py install-r-packages RobStatTM pyinit robustbase rrcov`.

---

## Step 6 — Check everything works

```bash
robstattm-py doctor
```

You are looking for **`Result: READY`** at the bottom. The report also shows
which R it found and which packages are installed.

If anything is wrong, the report says what and prints the command that fixes it.
The [troubleshooting guide](troubleshooting.md) covers each case in detail.

---

## Step 7 — Your first robust regression

Create a file called `first_fit.py` in your project folder with this content:

```python
import robstattm_py as rpm

# A dataset from the textbook: zinc and copper measured in pine needles.
mineral = rpm.datasets.mineral()
print(mineral.head())

# Fit a line predicting zinc from copper, robustly.
fit = rpm.lmrobdet_mm("zinc ~ copper", data=mineral)

print(fit.summary())
```

Run it:

```bash
python first_fit.py
```

You will see the first few rows of the data, then a table of coefficients.

> **A warning on the first fit is normal.** The first time R starts you may see
>
> ```text
> RobStatTMWarning: Registered S3 method overwritten by 'robustbase':
>   method from hatvalues.lmrob RobStatTM
> ```
>
> Both RobStatTM and `robustbase` define `hatvalues` for this kind of fit, so R
> announces which one it kept. It happens once per session, says nothing about
> your data, and a plain R session loading the same two packages prints it too.
> Nothing to fix.
>
> RobStatTM-Py deliberately shows you everything R says rather than hiding it —
> see [Seeing R warnings and errors](utilities.md). Warnings that *do* concern
> your data read very differently ("algorithm did not converge", for example).

### What just happened, line by line

- `import robstattm_py as rpm` — load the package, and call it `rpm` for short.
- `rpm.datasets.mineral()` — load a built-in dataset as a pandas DataFrame
  (a table). There are [20 built-in datasets](datasets.md).
- `"zinc ~ copper"` — a *formula*: "explain zinc using copper". This is R's
  notation, kept because it is compact and widely known.
- `lmrobdet_mm` — an **MM-estimator**: a regression that is not thrown off by a
  few unusual points.
- `fit.summary()` — the coefficient table.

### Why "robust"?

This dataset has one sample taken next to a copper mine. Ordinary least squares
chases that single point and reports a slope driven almost entirely by it. The
robust fit largely ignores it and describes the other 52 observations properly.

You can see the difference for yourself:

```python
import robstattm_py as rpm
import numpy as np

mineral = rpm.datasets.mineral()
robust = rpm.lmrobdet_mm("zinc ~ copper", data=mineral)

# Ordinary least squares, for comparison.
x = np.column_stack([np.ones(len(mineral)), mineral["copper"]])
ols = np.linalg.lstsq(x, mineral["zinc"], rcond=None)[0]

print(f"OLS slope:    {ols[1]:.3f}")
print(f"Robust slope: {robust.coefficients[1]:.3f}")
```

The two slopes differ by a wide margin. That gap is the outlier's influence.

---

## Where to go next

- [Your first analysis](../getting-started.md) — a fuller walkthrough.
- [Coming from R?](for-r-users.md) — every R name mapped to its Python one.
- [Datasets](datasets.md) — the 20 built-in textbook datasets.
- [Plotting](plotting.md) — diagnostic plots.
- [Checking your install](testing-for-beginners.md) — how to verify things and
  read an error when one appears.

## A short glossary

| Term | Meaning |
|---|---|
| **terminal** / shell | The window where you type commands. |
| **pip** | Python's package installer. `pip install X` fetches package X. |
| **virtual environment** | A private copy of Python for one project. |
| **PATH** | The list of folders your terminal searches for commands. "Not on PATH" means it could not find the program. |
| **package** | A bundle of reusable code. RobStatTM-Py is one. |
| **DataFrame** | A table of data, from the pandas library — rows and named columns. |
| **estimator** | A procedure that computes a number from data, e.g. a slope. |
| **outlier** | An observation far from the rest, which can distort ordinary methods. |
