"""Shared plumbing for the example scripts.

Kept deliberately thin. These scripts exist to show what using the package
looks like, so anything that would read as "framework" belongs here rather than
in the examples, and anything that reads as *statistics* belongs in the example
rather than here.

Three things live here:

``section`` / ``table``
    Consistent, diff-able console output, so a reader can hold the book open
    next to the terminal and compare numbers directly.

``figure``
    Every script is run non-interactively by ``tests/test_examples.py``, so
    figures are written to ``examples/_figures/`` rather than shown. Setting
    the Agg backend has to happen before ``pyplot`` is first imported, which is
    why importing this module is the first thing every script does.

``Skipped`` / ``require_r_packages``
    Eight of the book's scripts need R packages outside RobStatTM
    (``robustarima``, ``robustvarComp``, ``robcbi``, ``GSE``). Those must
    announce themselves and exit cleanly rather than traceback, so that a user
    without the optional dependency sees a sentence and the test suite records
    a skip instead of a failure.

``ols`` / ``l1_line``
    Non-robust comparators. Several scripts draw a least-squares or an L1 line
    purely as a foil for the robust fit. They are not estimators this package
    wraps and must not look like ones, so they live here as plain numpy rather
    than growing into wrappers.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np


def _use_headless_backend() -> None:
    """Select a non-interactive matplotlib backend, whenever we get here.

    The env var is the cheap path and works as long as nothing has imported
    pyplot yet. Importing this module first is what normally guarantees that,
    but import order is the kind of invariant a later edit quietly breaks — so
    if matplotlib is already loaded, switch it explicitly instead.
    """
    os.environ.setdefault("MPLBACKEND", "Agg")
    if "matplotlib" in sys.modules:  # pragma: no cover - depends on import order
        import matplotlib

        if matplotlib.get_backend().lower() not in {"agg", "pdf", "ps", "svg"}:
            matplotlib.use("Agg", force=True)


_use_headless_backend()

FIGURE_DIR = Path(__file__).resolve().parent / "_figures"

#: Exit status meaning "skipped, not failed" — the convention automake uses and
#: what ``tests/test_examples.py`` looks for.
EXIT_SKIPPED = 77


class Skipped(Exception):  # noqa: N818 - not an error; see below
    """Raised when an example cannot run because an optional R package is absent.

    Deliberately not named ``SkippedError``. Nothing has gone wrong when this is
    raised — it is control flow, the same role ``pytest.skip`` plays, and giving
    it an ``Error`` suffix would tell the reader the opposite of what happened.
    """


def section(title: str) -> None:
    """Print a section banner mirroring the source R script's comment blocks."""
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def table(title: str, rows: dict[str, object], *, fmt: str = "{:.4f}") -> None:
    """Print a labelled name/value table.

    Formats floats to a fixed width so successive runs — and a run against the
    book's printed tables — line up column-wise.
    """
    print(f"\n{title}")
    width = max((len(k) for k in rows), default=0)
    for key, value in rows.items():
        if isinstance(value, float):
            rendered = fmt.format(value)
        elif isinstance(value, (list, tuple)):
            rendered = "  ".join(
                fmt.format(v) if isinstance(v, float) else str(v) for v in value
            )
        else:
            rendered = str(value)
        print(f"  {key:<{width}}  {rendered}")


def figure(name: str) -> Path:
    """Return the path to write a figure to, creating the directory on demand."""
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURE_DIR / f"{name}.png"
    print(f"  [figure] {path}")
    return path


def require_python_packages(*names: str) -> None:
    """Raise :class:`Skipped` unless every named Python package is importable.

    A few examples reach for ``scipy`` or ``matplotlib`` to draw the non-robust
    comparator the R script plots alongside the robust fit. Those are example
    dependencies, not package dependencies — ``pip install "robstattm-py[examples]"``
    — so their absence is a skip, not a failure.
    """
    import importlib.util

    missing = [n for n in names if importlib.util.find_spec(n) is None]
    if missing:
        raise Skipped(
            f"needs the Python package(s) {', '.join(missing)}. Install with:\n"
            f'    pip install "robstattm-py[examples]"'
        )


def require_r_packages(*names: str) -> None:
    """Raise :class:`Skipped` unless every named R package can be loaded.

    Checks the packages the *example* needs, which is not always the set the
    wrapper needs — and does it up front, so a script that is going to be
    unrunnable says so before printing half a chapter of output.
    """
    from robstattm_py import RobStatTMSetupError
    from robstattm_py._r import require_r_pkg

    missing = []
    for name in names:
        try:
            require_r_pkg(name)
        except RobStatTMSetupError:
            missing.append(name)
    if missing:
        raise Skipped(
            f"needs the R package(s) {', '.join(missing)}. Install with:\n"
            f"    robstattm-py install-r-packages {' '.join(missing)}"
        )


def require_r_dataset(package: str, name: str) -> None:
    """Raise :class:`Skipped` unless a dataset from another R package is present.

    A dataset can be missing even when its package is installed, so guarding
    the package alone is not enough — that gap is what made an earlier CI run
    fail while every local run passed.
    """
    require_r_packages(package)
    from robstattm_py._r import r

    ok = bool(
        r().r(
            f'isTRUE(nzchar(system.file("data", package="{package}"))) && '
            f'"{name}" %in% data(package="{package}")$results[, "Item"]'
        )[0]
    )
    if not ok:
        raise Skipped(f"needs the dataset {name!r} from the R package {package!r}.")


def chisq_quantile(level: float, df: int) -> float:
    """Chi-squared quantile — R's ``qchisq(level, df)``.

    Chapter 6 compares Mahalanobis distances against a chi-squared cutoff in
    every example, so this needs to work with nothing but the package
    installed. scipy is used when present; otherwise the regularised lower
    incomplete gamma is summed directly and inverted by bisection, which is
    ample for a plotting cutoff.
    """
    try:
        from scipy import stats

        return float(stats.chi2.ppf(level, df))
    except ImportError:
        from math import exp, lgamma, log

        def cdf(x: float) -> float:
            a = df / 2.0
            total = term = 1.0 / a
            for k in range(1, 1000):
                term *= (x / 2.0) / (a + k)
                total += term
                if term < total * 1e-15:
                    break
            return exp(-x / 2.0 + a * log(x / 2.0) - lgamma(a)) * total

        low, high = 1e-12, 1e4
        for _ in range(200):
            mid = (low + high) / 2.0
            if cdf(mid) < level:
                low = mid
            else:
                high = mid
        return (low + high) / 2.0


def ols(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Return ``(intercept, slope)`` of the least-squares line — R's ``lm(y ~ x)``."""
    design = np.column_stack([np.ones_like(x), x])
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    return float(coef[0]), float(coef[1])


def l1_line(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Return ``(intercept, slope)`` minimising the sum of absolute residuals.

    Stands in for ``quantreg::rq(y ~ x)``. With one predictor the L1 optimum
    passes through two of the data points, so scoring every pair gives an exact
    answer — 120 pairs for the shock data, 1378 for mineral. Direct, and it
    avoids taking on a dependency for what is only a comparison line.
    """
    n = len(x)
    best_loss, best = np.inf, (0.0, 0.0)
    for i in range(n):
        for j in range(i + 1, n):
            if x[i] == x[j]:
                continue
            slope = (y[j] - y[i]) / (x[j] - x[i])
            intercept = y[i] - slope * x[i]
            loss = float(np.sum(np.abs(y - (intercept + slope * x))))
            if loss < best_loss:
                best_loss, best = loss, (float(intercept), float(slope))
    return best


def ml_logistic(x: np.ndarray, y: np.ndarray, *, tol: float = 1e-10) -> np.ndarray:
    """Maximum-likelihood logistic regression by IRLS — R's ``glm(binomial)``.

    The non-robust baseline for Chapter 7. Returns ``[intercept, *slopes]``.
    """
    design = np.column_stack([np.ones(len(y)), x])
    beta = np.zeros(design.shape[1])
    for _ in range(100):
        eta = design @ beta
        mu = 1.0 / (1.0 + np.exp(-eta))
        w = np.clip(mu * (1 - mu), 1e-10, None)
        z = eta + (y - mu) / w
        root_w = np.sqrt(w)
        step = np.linalg.lstsq(design * root_w[:, None], z * root_w, rcond=None)[0]
        converged = np.max(np.abs(step - beta)) < tol
        beta = step
        if converged:
            break
    return beta


def ml_deviance_residuals(
    x: np.ndarray, y: np.ndarray, beta: np.ndarray
) -> np.ndarray:
    """Signed deviance residuals — R's ``resid(fit, type = "deviance")``."""
    design = np.column_stack([np.ones(len(y)), x])
    mu = np.clip(1.0 / (1.0 + np.exp(-(design @ beta))), 1e-12, 1 - 1e-12)
    deviance = -2.0 * (y * np.log(mu) + (1 - y) * np.log(1 - mu))
    return np.sign(y - mu) * np.sqrt(deviance)


def run(main) -> None:
    """Run an example's ``main`` and translate :class:`Skipped` into an exit code.

    Use as::

        if __name__ == "__main__":
            run(main)
    """
    try:
        main()
    except Skipped as exc:
        print(f"\nSKIPPED: {exc}")
        sys.exit(EXIT_SKIPPED)
