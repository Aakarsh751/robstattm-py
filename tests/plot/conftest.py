"""Fixtures for the native plotting tests.

These tests are **R-free**: they build a duck-typed fit carrying the same arrays
a real ``lmrobdet_mm`` result exposes, so they exercise the native renderers
without starting R (and let us assert the no-refit contract). matplotlib is
required; tests skip cleanly when the ``[plots]`` extra is absent.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

# matplotlib lives behind the optional ``[plots]`` extra. When it is absent
# (e.g. the default CI test job), skip collecting the whole tests/plot tree
# instead of erroring at import time. A headless backend is forced up front so
# no test ever needs a display.
try:
    import matplotlib

    matplotlib.use("Agg", force=True)
    _HAVE_MPL = True
except ImportError:  # pragma: no cover - exercised on the no-extras CI job
    _HAVE_MPL = False
    collect_ignore_glob = ["test_*.py"]


@pytest.fixture
def fake_fit():
    """A duck-typed robust regression fit with planted outliers."""
    rng = np.random.default_rng(7)
    n = 50
    fitted = np.linspace(-2.0, 12.0, n)
    resid = rng.normal(0.0, 1.0, n)
    resid[4] = 9.0      # big positive residual
    resid[19] = -8.0    # big negative residual
    scale = 1.0
    std = resid / scale
    rweights = np.clip(1.0 - np.abs(std) / 6.0, 0.0, 1.0)
    return SimpleNamespace(
        residuals=resid,
        fitted_values=fitted,
        rweights=rweights,
        scale=scale,
        # leverage source for resid_vs_leverage (avoids any R refit)
        _leverage=np.abs(rng.normal(0.1, 0.05, n)),
        hatvalues=lambda: np.abs(rng.normal(0.1, 0.05, n)),
    )


@pytest.fixture
def fake_cov_pair():
    """Duck-typed (robust, classical) covariance results with squared dists."""
    rng = np.random.default_rng(11)
    n = 45
    cov = np.array([[1.0, 0.6, 0.1, 0.0],
                    [0.6, 1.0, 0.2, 0.1],
                    [0.1, 0.2, 1.0, 0.3],
                    [0.0, 0.1, 0.3, 1.0]])
    rdist = np.abs(rng.normal(3.0, 2.0, n))
    rdist[2] = 25.0  # planted multivariate outlier
    rdist[9] = 18.0
    cdist = np.abs(rng.normal(3.0, 1.5, n))
    robust = SimpleNamespace(dist=rdist, cov=cov, cor=None,
                             column_names=("a", "b", "c", "d"), classical=False)
    classical = SimpleNamespace(dist=cdist, cov=cov * 0.8, cor=None,
                                column_names=("a", "b", "c", "d"), classical=True)
    return robust, classical


@pytest.fixture
def fake_pca():
    """Duck-typed robust PCA result (pca_rob_s shape)."""
    rng = np.random.default_rng(13)
    n, p, q = 45, 4, 3
    return SimpleNamespace(
        repre=rng.normal(0.0, 1.0, (n, q)),
        eigvec=rng.normal(0.0, 1.0, (p, q)),
        prop_spc=np.array([0.55, 0.30, 0.15]),
        column_names=("a", "b", "c", "d"),
    )


@pytest.fixture
def fake_locscale():
    return SimpleNamespace(mu=0.2, std_mu=0.1, disper=0.9)


@pytest.fixture
def fake_reg_with_data():
    """Duck-typed simple-regression fit carrying its DataFrame."""
    import pandas as pd

    rng = np.random.default_rng(17)
    n = 40
    copper = rng.uniform(1.0, 9.0, n)
    zinc = 2.0 + 1.3 * copper + rng.normal(0.0, 1.0, n)
    zinc[3] += 9.0
    df = pd.DataFrame({"zinc": zinc, "copper": copper})
    resid = rng.normal(0.0, 1.0, n)
    return SimpleNamespace(
        residuals=resid,
        fitted_values=2.0 + 1.3 * copper,
        rweights=np.clip(rng.uniform(0.2, 1.0, n), 0, 1),
        scale=1.0,
        coef_names=("(Intercept)", "copper"),
        coefficients=np.array([2.0, 1.3]),
        formula="zinc ~ copper",
        _data=df,
    )


@pytest.fixture(autouse=True)
def _reset_theme():
    """Keep the global theme isolated between tests."""
    from robstattm_py.plot import _style

    saved = _style.get_theme()
    yield
    _style.set_theme(saved)


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    if _HAVE_MPL:
        import matplotlib.pyplot as plt

        plt.close("all")
