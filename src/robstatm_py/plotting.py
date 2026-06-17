"""Plotting helpers — Path A (R graphics via rpy2 PNG device).

Per ``docs/plotting_strategy.md`` (decision D-008) the preferred plotting
backend is R's own graphics device. We open a PNG device, run the R plot
expression, close the device, and return a path to the resulting file.
The user can ``display`` it in Jupyter or embed it elsewhere.

Why R-side: fidelity. The textbook's published figures are rendered by R;
calling the same plotting functions through rpy2 gives pixel-perfect
parity (subject to OS-level font and DPI differences).

Example
-------
>>> from robstatm_py.plotting import r_plot, show_png
>>> path = r_plot('''
...     library(RobStatTM); data(mineral)
...     plot(zinc ~ copper, data=mineral, pch=19)
... ''')
>>> show_png(path)   # in Jupyter
"""
from __future__ import annotations

import pathlib
import tempfile
import uuid
from typing import Optional

from robstatm_py._r import r, r_pkg


def r_plot(
    r_code: str,
    *,
    dpi: int = 100,
    width: float = 6.0,
    height: float = 5.0,
    path: Optional[pathlib.Path] = None,
    bg: str = "white",
) -> pathlib.Path:
    """Run ``r_code`` against an open PNG device and return the file path.

    Parameters
    ----------
    r_code : str
        R expression(s) that draw on the current graphics device. Anything
        ``plot()`` / ``abline()`` / ``text()`` etc. works. Do NOT call
        ``dev.off()`` yourself — this function manages the device.
    dpi : int, default 100
        Resolution in dots per inch.
    width, height : float, default 6.0, 5.0
        Figure dimensions in inches.
    path : pathlib.Path, optional
        Where to write the PNG. Default: a fresh temp file.
    bg : str, default "white"
        R background color (``bg`` argument to ``png()``).

    Returns
    -------
    pathlib.Path
        The PNG file path. Read or display it however you like.
    """
    ro = r()
    _ = r_pkg("RobStatTM")  # ensure attached so example data is loadable

    if path is None:
        tmpdir = pathlib.Path(tempfile.gettempdir())
        path = tmpdir / f"robstatm_py_plot_{uuid.uuid4().hex}.png"
    else:
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

    posix = path.as_posix()
    ro.r(
        f'png(file="{posix}", width={width}, height={height}, '
        f'units="in", res={int(dpi)}, bg="{bg}")'
    )
    try:
        ro.r(r_code)
    finally:
        ro.r("dev.off()")
    return path


def _refit_and_run(fit: object, plot_expr: str, **kw) -> pathlib.Path:
    """Internal: replay an `lmrobdet*` fit in R, then run ``plot_expr``.

    ``plot_expr`` is an R expression that may reference ``rpm_diag_fit``
    (the freshly re-fit R model) and ``rpm_diag_df`` (the data frame).
    """
    from robstatm_py._r import r as _rmod
    from robstatm_py.regression._formula import push_df_to_r

    formula = getattr(fit, "formula", None)
    data = getattr(fit, "_data", None)
    if formula is None or data is None:
        raise RuntimeError(
            f"Cannot plot diagnostics for {type(fit).__name__}: missing "
            "`formula` and `_data` (likely unpickled — plotting requires "
            "the original DataFrame)."
        )
    ro = _rmod()
    push_df_to_r(data, var_name="rpm_diag_df")
    fitter = type(fit).__name__
    rfn_name = {
        "LmrobdetMMResult":   "lmrobdetMM",
        "LmrobdetDCMLResult": "lmrobdetDCML",
        "LmrobMResult":       "lmrobM",
    }.get(fitter)
    if rfn_name is None:
        raise TypeError(
            f"Diagnostic plotting not supported for {fitter}; expected an "
            "lmrobdet_mm / lmrobdet_dcml / lmrob_m result."
        )
    # Reuse the fit's own control (the converted handle lost its S3 class), so
    # the diagnostic plots show the user's actual model, not a default-control
    # refit. Same fix as the S3-method ports.
    r_control = getattr(fit, "_r_control", None)
    cleanup = ["rpm_diag_fit", "rpm_diag_df"]
    if r_control is not None:
        ro.globalenv["rpm_diag_ctrl"] = r_control
        cleanup.append("rpm_diag_ctrl")
        r_call = f"{rfn_name}({formula}, data=rpm_diag_df, control=rpm_diag_ctrl)"
    else:
        r_call = f"{rfn_name}({formula}, data=rpm_diag_df)"
    ro.r(f"library(RobStatTM); rpm_diag_fit <- {r_call}")
    try:
        path = r_plot(plot_expr, **kw)
    finally:
        ro.r(
            "for (v in c("
            + ",".join(f"'{v}'" for v in cleanup)
            + ")) if (exists(v)) rm(list=v)"
        )
    return path


def residuals(fit: object, **kw) -> pathlib.Path:
    """Residuals-vs-fitted plot for any lmrobdet* fit.

    Mirrors R's ``plot(fit, which = 1)``.
    """
    return _refit_and_run(
        fit,
        "plot(fitted(rpm_diag_fit), residuals(rpm_diag_fit), "
        " pch=19, col='steelblue',"
        " xlab='Fitted values', ylab='Residuals',"
        " main='Residuals vs Fitted');"
        "abline(h=0, col='gray50', lty=2)",
        **kw,
    )


def qq(fit: object, **kw) -> pathlib.Path:
    """Normal Q-Q plot of standardized residuals.

    Mirrors R's ``plot(fit, which = 2)``.
    """
    return _refit_and_run(
        fit,
        "qqnorm(residuals(rpm_diag_fit)/rpm_diag_fit$scale, "
        " pch=19, col='steelblue',"
        " main='Normal Q-Q (standardized residuals)');"
        "qqline(residuals(rpm_diag_fit)/rpm_diag_fit$scale, col='firebrick')",
        **kw,
    )


def diagnostics(fit: object, **kw) -> pathlib.Path:
    """2x2 diagnostic panel: residuals vs fitted, Q-Q, scale-location, weights.

    Mirrors the spirit of R's ``plot(lm(...))`` four-panel diagnostic.
    """
    return _refit_and_run(
        fit,
        """
        par(mfrow=c(2,2), mar=c(4,4,3,1))
        plot(fitted(rpm_diag_fit), residuals(rpm_diag_fit),
             pch=19, col='steelblue',
             xlab='Fitted', ylab='Residuals',
             main='Residuals vs Fitted')
        abline(h=0, col='gray50', lty=2)
        qqnorm(residuals(rpm_diag_fit)/rpm_diag_fit$scale,
               pch=19, col='steelblue',
               main='Normal Q-Q')
        qqline(residuals(rpm_diag_fit)/rpm_diag_fit$scale, col='firebrick')
        plot(fitted(rpm_diag_fit), sqrt(abs(residuals(rpm_diag_fit)/rpm_diag_fit$scale)),
             pch=19, col='steelblue',
             xlab='Fitted', ylab=expression(sqrt(abs(std.resid))),
             main='Scale-Location')
        plot(rpm_diag_fit$rweights,
             pch=19, col='steelblue',
             xlab='Observation index', ylab='Robust weight',
             main='Robust weights')
        abline(h=1, col='gray70', lty=3)
        par(mfrow=c(1,1))
        """,
        width=kw.pop("width", 8.0),
        height=kw.pop("height", 7.0),
        **kw,
    )


def show_png(path: pathlib.Path):
    """Display a PNG in Jupyter (returns an ``IPython.display.Image``).

    Raises ``ImportError`` if IPython is not installed (it is part of any
    Jupyter environment, so this should always work in notebooks).
    """
    try:
        from IPython.display import Image
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "IPython is required for show_png. Install with "
            "`pip install ipython` (or just use jupyter)."
        ) from e
    return Image(filename=str(path))
