"""Run an appropriate estimator on each of the 20 RobStatTM datasets.

The main ``tests/datasets/`` module verifies *loading* only. Here we verify
that each dataset supports a realistic textbook-style workflow end-to-end.

Workflows mirror ``robstattm/examples-scripts/`` where available; otherwise
a sensible default is chosen and documented in the table below.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pytest

import robstattm_py as rpm
from tests.conftest import needs_r


@dataclass(frozen=True)
class DatasetWorkflow:
    loader: str
    description: str
    run: Callable[[], object]


BOOK = rpm.lmrobdet_control(bb=0.5, efficiency=0.85, family="bisquare")


def _last_col_mm(loader: str):
    df = getattr(rpm.datasets, loader)()
    y = df.attrs["r_columns"][-1]
    return rpm.lmrobdet_mm(f"{y} ~ .", data=df)


def _make_workflows() -> list[DatasetWorkflow]:
    return [
        DatasetWorkflow(
            "alcohol",
            "MM regression, log(Solubility) vs molecular descriptors (Ch.2)",
            lambda: _last_col_mm("alcohol"),
        ),
        DatasetWorkflow(
            "algae",
            "MM dot-formula (Example 5.4)",
            lambda: rpm.lmrobdet_mm(
                "V12 ~ .", data=rpm.datasets.algae(), control=BOOK
            ),
        ),
        DatasetWorkflow(
            "biochem",
            "Robust covariance on 2-var scatter (Example 6.1)",
            lambda: rpm.cov_rob_mm(rpm.datasets.biochem().to_numpy()),
        ),
        DatasetWorkflow(
            "breslow_dat",
            "MM on epilepsy counts, Ysum vs baseline covariates",
            lambda: rpm.lmrobdet_mm("Ysum ~ Base + Age10 + Base4", data=rpm.datasets.breslow_dat()),
        ),
        DatasetWorkflow(
            "bus",
            "Robust PCA on image features (Example 6.x)",
            lambda: rpm.prcomp_rob(rpm.datasets.bus().to_numpy(), rank=5),
        ),
        DatasetWorkflow(
            "flour",
            "Univariate locScaleM (Example 4.x flour.R)",
            lambda: rpm.loc_scale_m(
                rpm.datasets.flour().iloc[:, 0].to_numpy(), eff=0.95
            ),
        ),
        DatasetWorkflow(
            "glass",
            "MM covariance (p=7)",
            lambda: rpm.cov_rob(rpm.datasets.glass().to_numpy()),
        ),
        DatasetWorkflow(
            "hearing",
            "Univariate locScaleM on first audiometry channel",
            lambda: rpm.loc_scale_m(
                rpm.datasets.hearing().iloc[:, 0].to_numpy(), eff=0.95
            ),
        ),
        DatasetWorkflow(
            "image",
            "Rocke covariance on large segmentation data",
            lambda: rpm.cov_rob_rocke(rpm.datasets.image().to_numpy()),
        ),
        DatasetWorkflow(
            "leuk_dat",
            "Weighted BY logistic (Example 7.1 style)",
            lambda: _leuk_wby(),
        ),
        DatasetWorkflow(
            "mineral",
            "Flagship MM regression (Example 5.1)",
            lambda: rpm.lmrobdet_mm("zinc ~ copper", data=rpm.datasets.mineral()),
        ),
        DatasetWorkflow(
            "neuralgia",
            "BY logistic on clinical trial",
            lambda: _neuralgia_by(),
        ),
        DatasetWorkflow(
            "oats",
            "M regression ANOVA-style (Example 4.2)",
            lambda: rpm.lmrob_m(
                "response1 ~ variety + block",
                data=rpm.datasets.oats(),
                control=rpm.lmrobm_control(
                    bb=0.5, efficiency=0.85, family="bisquare"
                ),
            ),
        ),
        DatasetWorkflow(
            "resex",
            "Univariate locScaleM on residence-time series",
            lambda: rpm.loc_scale_m(
                rpm.datasets.resex()["resex"].to_numpy(), psi="bisquare"
            ),
        ),
        DatasetWorkflow(
            "shock",
            "M regression (Example 4.1 shock.R)",
            lambda: rpm.lmrob_m(
                "time ~ n.shocks",
                data=rpm.datasets.shock(),
                control=rpm.lmrobm_control(
                    bb=0.5, efficiency=0.85, family="bisquare"
                ),
            ),
        ),
        DatasetWorkflow(
            "skin",
            "BY logistic (Example 7.x skin.R)",
            lambda: _skin_by(),
        ),
        DatasetWorkflow(
            "stackloss",
            "MM on classic stackloss",
            lambda: rpm.lmrobdet_mm(
                "stack.loss ~ Air.Flow + Water.Temp + Acid.Conc.",
                data=rpm.datasets.stackloss(),
            ),
        ),
        DatasetWorkflow(
            "vehicle",
            "Rocke covariance on silhouettes (p=18)",
            lambda: rpm.cov_rob(rpm.datasets.vehicle().to_numpy()),
        ),
        DatasetWorkflow(
            "waste",
            "MM regression, solid waste vs land-use predictors",
            lambda: _last_col_mm("waste"),
        ),
        DatasetWorkflow(
            "wine",
            "MM covariance on cultivars (Example 6.3)",
            lambda: rpm.cov_rob_mm(rpm.datasets.wine().to_numpy()),
        ),
    ]


def _skin_by():
    df = rpm.datasets.skin()
    X = df[["logVOL", "logRATE"]].to_numpy(dtype=float)
    y = df["vasoconst"].to_numpy(dtype=float)
    return rpm.by_logreg(X, y)


def _leuk_wby():
    df = rpm.datasets.leuk_dat()
    X = df.iloc[:, :2].to_numpy(dtype=float)
    y = df["y"].to_numpy(dtype=float)
    return rpm.wby_logreg(X, y)


def _neuralgia_by():
    df = rpm.datasets.neuralgia()
    y = df["Y"].to_numpy(dtype=float)
    # Treatment / Sex are factors in R; use numeric Age + Complaint + coded factors.
    treat = (df["Treatment"].astype(str) != "0").astype(float).to_numpy()
    sex = (df["Sex"].astype(str) == "M").astype(float).to_numpy()
    age = df["Age"].to_numpy(dtype=float)
    complaint = df["Complaint"].to_numpy(dtype=float)
    X = np.column_stack([age, complaint, treat, sex])
    return rpm.by_logreg(X, y)


WORKFLOWS = _make_workflows()


@needs_r
@pytest.mark.parametrize(
    "wf",
    WORKFLOWS,
    ids=[w.loader for w in WORKFLOWS],
)
def test_dataset_workflow_runs(wf: DatasetWorkflow):
    """Each dataset completes a representative fit without error."""
    rpm.set_seed(42)
    result = wf.run()
    assert result is not None, wf.description


@needs_r
@pytest.mark.parametrize(
    "wf",
    [w for w in WORKFLOWS if w.loader in ("mineral", "wine", "flour", "skin")],
    ids=lambda w: w.loader,
)
def test_key_datasets_finite_outputs(wf: DatasetWorkflow):
    """Spot-check numerical sanity on flagship datasets."""
    rpm.set_seed(42)
    result = wf.run()
    if hasattr(result, "scale"):
        assert np.isfinite(result.scale) and result.scale > 0
    elif hasattr(result, "center"):
        assert np.all(np.isfinite(result.center))
    elif hasattr(result, "coefficients"):
        assert np.all(np.isfinite(result.coefficients))
