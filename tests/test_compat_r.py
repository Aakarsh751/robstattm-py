"""Tests for ``robstatm_py.compat_r`` — R-name alias layer."""
from __future__ import annotations

import pytest

import robstatm_py as rpm
from robstatm_py import compat_r


class TestRNameAliases:

    def test_lmrobdetMM_is_lmrobdet_mm(self):
        assert compat_r.lmrobdetMM is rpm.lmrobdet_mm

    def test_lmrobdetDCML_alias(self):
        assert compat_r.lmrobdetDCML is rpm.lmrobdet_dcml

    def test_lmrobM_alias(self):
        assert compat_r.lmrobM is rpm.lmrob_m

    def test_covRobMM_alias_and_R_alias(self):
        assert compat_r.covRobMM is rpm.cov_rob_mm
        assert compat_r.MMultiSHR is rpm.cov_rob_mm

    def test_covRob_aliases(self):
        assert compat_r.covRob is rpm.cov_rob
        assert compat_r.Multirobu is rpm.cov_rob

    def test_glm_aliases(self):
        assert compat_r.BYlogreg is rpm.by_logreg
        assert compat_r.logregBY is rpm.by_logreg
        assert compat_r.WMLlogreg is rpm.wml_logreg

    def test_psi_aliases(self):
        assert compat_r.bisquare is rpm.psi.bisquare
        assert compat_r.rho is rpm.psi.rho

    def test_pcaRobS_alias_and_R_alias(self):
        assert compat_r.pcaRobS is rpm.pca_rob_s
        assert compat_r.SMPCA is rpm.pca_rob_s

    def test_INVTR2_alias(self):
        assert compat_r.INVTR2 is rpm.invtr2

    def test_control_factory_aliases(self):
        assert compat_r.lmrobM_control is rpm.lmrobm_control
        assert compat_r.lmrobdet_control is rpm.lmrobdet_control


class TestDataHelper:

    def test_data_loads_mineral(self):
        df = compat_r.data("mineral")
        assert df.shape == (53, 2)

    def test_data_unknown_dataset_raises(self):
        with pytest.raises(KeyError, match="not found"):
            compat_r.data("not_a_dataset_at_all")


def test_compat_r_dir_is_clean():
    """``from robstatm_py.compat_r import *`` should expose the R names
    but not pollute with private symbols."""
    public = set(compat_r.__all__)
    # No private symbols leaked
    assert not any(n.startswith("_") for n in public)
    # Headline names present
    for name in ("lmrobdetMM", "covRobMM", "prcompRob", "BYlogreg"):
        assert name in public
