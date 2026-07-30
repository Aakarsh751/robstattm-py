"""Covariance: cross-estimator consistency, classical-vs-numpy parity, index
semantics, and seed determinism.

Distinct from ``tests/covariance/*`` (which is per-estimator strict parity) and
from ``exploration`` (data pipelines): these assert relationships *between*
estimators and Python-side invariants.
"""
from __future__ import annotations

import numpy as np
import pytest

import robstattm_py as rpm
from tests.conftest import needs_r


def _small_wine(p=4):
    return rpm.datasets.wine().iloc[:, :p]


@needs_r
class TestCovRobDispatchConsistency:
    """covRob(type=…) must equal the directly-called sub-estimator (same seed)."""

    def test_forced_mm_equals_cov_rob_mm(self):
        X = _small_wine(4).to_numpy()
        rpm.set_seed(11)
        a = rpm.cov_rob(X, type="MM")
        rpm.set_seed(11)
        b = rpm.cov_rob_mm(X)
        np.testing.assert_array_equal(a.cov, b.cov)
        np.testing.assert_array_equal(a.center, b.center)
        assert a.estimator_type == "MM"

    def test_forced_rocke_equals_cov_rob_rocke(self):
        X = rpm.datasets.wine().to_numpy()  # p=13
        rpm.set_seed(3)
        a = rpm.cov_rob(X, type="Rocke")
        rpm.set_seed(3)
        b = rpm.cov_rob_rocke(X)
        np.testing.assert_array_equal(a.cov, b.cov)
        assert a.estimator_type == "Rocke"

    def test_auto_label_tracks_dimension(self):
        rpm.set_seed(1)
        small = rpm.cov_rob(_small_wine(4).to_numpy(), type="auto")
        assert small.estimator_type == "MM"
        rpm.set_seed(1)
        big = rpm.cov_rob(rpm.datasets.wine().to_numpy(), type="auto")
        assert big.estimator_type == "Rocke"


@needs_r
class TestCovClassicVsNumpy:
    def test_center_is_column_mean(self):
        X = _small_wine(5).to_numpy()
        res = rpm.cov_classic(X)
        np.testing.assert_allclose(res.center, X.mean(axis=0), rtol=1e-9)

    def test_unbiased_matches_numpy_ddof1(self):
        X = _small_wine(5).to_numpy()
        res = rpm.cov_classic(X, unbiased=True)
        np.testing.assert_allclose(res.cov, np.cov(X, rowvar=False, ddof=1), rtol=1e-9)

    def test_biased_is_unbiased_scaled(self):
        X = _small_wine(5).to_numpy()
        n = X.shape[0]
        unb = rpm.cov_classic(X, unbiased=True).cov
        bia = rpm.cov_classic(X, unbiased=False).cov
        np.testing.assert_allclose(bia, unb * (n - 1) / n, rtol=1e-9)

    def test_distance_false_yields_none(self):
        res = rpm.cov_classic(_small_wine(3), distance=False)
        assert res.dist is None

    def test_corr_true_populates_cor(self):
        res = rpm.cov_classic(_small_wine(4), corr=True)
        assert res.cor is not None
        np.testing.assert_allclose(np.diag(res.cor), np.ones(4), rtol=1e-9)


@needs_r
class TestInitialEstimatorInvariants:
    def test_kurt_sd_idx_is_binary_mask(self):
        rpm.set_seed(5)
        res = rpm.kurt_sd_new(_small_wine(4))
        uniq = set(np.unique(res.idx).tolist())
        assert uniq <= {0.0, 1.0}
        assert res.center.shape == (4,)

    def test_fastmve_best_is_zero_based_in_range(self):
        X = _small_wine(4).to_numpy()
        rpm.set_seed(9)
        res = rpm.fastmve(X)
        assert res.best.min() >= 0
        assert res.best.max() < X.shape[0]
        # the indices must be usable to slice X
        assert X[res.best].shape[1] == 4
        # covariance is symmetric
        np.testing.assert_allclose(res.cov, res.cov.T, rtol=1e-12)


@needs_r
class TestSeedDeterminism:
    def test_cov_rob_mm_reproducible(self):
        X = _small_wine(5).to_numpy()
        rpm.set_seed(123)
        a = rpm.cov_rob_mm(X)
        rpm.set_seed(123)
        b = rpm.cov_rob_mm(X)
        np.testing.assert_array_equal(a.cov, b.cov)

    def test_summary_evals_sorted_and_normalised(self):
        res = rpm.cov_classic(_small_wine(5))
        s = res.summary()
        # eigenvalues descending
        assert np.all(np.diff(s.evals) <= 1e-9)
        # proportions sum to 1
        assert abs(float(s.proportion_of_variance.sum()) - 1.0) < 1e-9
