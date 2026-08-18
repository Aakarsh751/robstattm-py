"""Strict-tier tests for var_comprob vs direct R (robustvarComp package).

Reproduces the autism.R example (Example 6.7): the Composite-Tau and Classic-S
variance-component fits. ``varComprob`` is stochastic, so each fit is run with an
identical ``set.seed`` in both the R reference and the Python wrapper, on
identical inputs (the prepared autism frame is pulled from R; the K kernels and
groups matrix are rebuilt deterministically in Python).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import robstattm_py as rpm
from robstattm_py import set_seed
from tests.conftest import needs_robustvarcomp, needs_wwgbook

_FIXED = (
    "vsae ~ age.2 + I(age.2^2) + sicdegp2.f + age.2:sicdegp2.f + I(age.2^2):sicdegp2.f"
)
_SEED = 2468

_R_PREP = """
data(autism, package='WWGbook')
autism <- autism[complete.cases(autism),]
completi <- table(autism$childid)==5
completi <- names(completi[completi])
indici <- as.vector(unlist(sapply(completi, function(x) which(autism$childid==x))))
ind <- rep(FALSE, nrow(autism)); ind[indici] <- TRUE
autism <- subset(autism, subset=ind)
sicdegp <- autism$sicdegp; age <- autism$age
age.2 <- age - 2
sicdegp2 <- sicdegp
sicdegp2[sicdegp == 3] <- 0; sicdegp2[sicdegp == 2] <- 2; sicdegp2[sicdegp == 1] <- 1
sicdegp2.f <- factor(sicdegp2)
autism.updated <- subset(data.frame(autism, sicdegp2.f, age.2), !is.na(vsae))
p <- 5; n <- 41
z1 <- rep(1, p); z2 <- c(0, 1, 3, 7, 11); z3 <- z2^2
K <- list(); K[[1]] <- tcrossprod(z1,z1); K[[2]] <- tcrossprod(z2,z2); K[[3]] <- tcrossprod(z3,z3)
K[[4]] <- tcrossprod(z1,z2)+tcrossprod(z2,z1)
K[[5]] <- tcrossprod(z1,z3)+tcrossprod(z3,z1)
K[[6]] <- tcrossprod(z3,z2)+tcrossprod(z2,z3)
names(K) <- c("Int","age","age2","Int:age","Int:age2","age:age2")
groups <- cbind(rep(1:p, each=n), rep((1:n), p))
"""


def _pull_autism_df(R) -> pd.DataFrame:
    """Rebuild the prepared autism frame column-by-column.

    Pulling the whole R data.frame via the active pandas2ri converter trips
    "Per-column arrays must each be 1-dimensional"; building from individual
    columns (verified to give a bit-identical model matrix) sidesteps it.
    """
    vsae = np.asarray(R("as.numeric(autism.updated$vsae)"), dtype=float)
    age2 = np.asarray(R("as.numeric(autism.updated[['age.2']])"), dtype=float)
    codes = np.asarray(R("as.integer(autism.updated[['sicdegp2.f']])"), dtype=int) - 1
    levels = [str(x) for x in R("levels(autism.updated[['sicdegp2.f']])")]
    sic = pd.Categorical.from_codes(codes, categories=levels)
    return pd.DataFrame({"vsae": vsae, "age.2": age2, "sicdegp2.f": sic})


def _build_inputs():
    """Build the K kernels, groups matrix and names exactly as autism.R does."""
    p, n = 5, 41
    z1 = np.ones(p)
    z2 = np.array([0.0, 1.0, 3.0, 7.0, 11.0])
    z3 = z2**2
    K = [
        np.outer(z1, z1),
        np.outer(z2, z2),
        np.outer(z3, z3),
        np.outer(z1, z2) + np.outer(z2, z1),
        np.outer(z1, z3) + np.outer(z3, z1),
        np.outer(z3, z2) + np.outer(z2, z3),
    ]
    names = ("Int", "age", "age2", "Int:age", "Int:age2", "age:age2")
    groups = np.column_stack(
        [np.repeat(np.arange(1, p + 1), n), np.tile(np.arange(1, n + 1), p)]
    )
    return K, names, groups


@needs_robustvarcomp
@needs_wwgbook
class TestAutismCompositeTau:
    """autism.R, Composite-Tau fit (default method)."""

    @pytest.fixture(scope="class")
    def setup(self, R):
        R(_R_PREP)
        # R reference (Composite Tau)
        R("ctrl <- robustvarComp::varComprob.control(lower=c(0.01,0.01,0.01,-Inf,-Inf,-Inf))")
        R(f"set.seed({_SEED}L); rfit <- robustvarComp::varComprob({_FIXED}, groups=groups, "
          "data=autism.updated, varcov=K, control=ctrl)")
        # pull the prepared frame into pandas
        df = _pull_autism_df(R)
        K, names, groups = _build_inputs()
        ctrl = rpm.var_comprob_control(lower=[0.01, 0.01, 0.01, -np.inf, -np.inf, -np.inf])
        set_seed(_SEED)
        py = rpm.var_comprob(
            _FIXED, df, groups=groups, varcov=K, varcov_names=names, control=ctrl
        )
        return py

    def test_beta(self, setup, R):
        np.testing.assert_array_equal(
            setup.beta, np.asarray(R("as.numeric(rfit$beta)"), dtype=float)
        )

    def test_eta(self, setup, R):
        np.testing.assert_array_equal(
            setup.eta, np.asarray(R("as.numeric(rfit$eta)"), dtype=float)
        )

    def test_gamma(self, setup, R):
        np.testing.assert_array_equal(
            setup.gamma, np.asarray(R("as.numeric(rfit$gamma)"), dtype=float)
        )

    def test_sigma2(self, setup, R):
        assert setup.sigma2 == float(R("as.numeric(rfit$sigma2)")[0])

    def test_Sigma(self, setup, R):
        np.testing.assert_array_equal(
            setup.Sigma, np.asarray(R("rfit$Sigma"), dtype=float)
        )

    def test_vcov_beta(self, setup, R):
        np.testing.assert_array_equal(
            setup.vcov_beta, np.asarray(R("rfit$vcov.beta"), dtype=float)
        )

    def test_method(self, setup):
        assert setup.method == "compositeTau"
        assert setup.beta.shape[0] == 9 and setup.eta.shape[0] == 6

    def test_beta_names(self, setup, R):
        assert setup.beta_names == tuple(str(n) for n in R("names(rfit$beta)"))

    def test_repr(self, setup):
        assert "VarComprobResult" in repr(setup)


@needs_robustvarcomp
@needs_wwgbook
class TestAutismClassicS:
    """autism.R, Classic-S fit (method='S', psi='rocke', cov.init='covOGK')."""

    @pytest.fixture(scope="class")
    def setup(self, R):
        R(_R_PREP)
        R("ctrl2 <- robustvarComp::varComprob.control(method='S', psi='rocke', cov.init='covOGK', "
          "lower=c(0.01,0.01,0.01,-Inf,-Inf,-Inf))")
        R(f"set.seed({_SEED}L); rfitS <- robustvarComp::varComprob({_FIXED}, groups=groups, "
          "data=autism.updated, varcov=K, control=ctrl2)")
        df = _pull_autism_df(R)
        K, names, groups = _build_inputs()
        ctrl = rpm.var_comprob_control(
            method="S", psi="rocke", cov_init="covOGK",
            lower=[0.01, 0.01, 0.01, -np.inf, -np.inf, -np.inf],
        )
        set_seed(_SEED)
        py = rpm.var_comprob(
            _FIXED, df, groups=groups, varcov=K, varcov_names=names, control=ctrl
        )
        return py

    def test_beta(self, setup, R):
        np.testing.assert_array_equal(
            setup.beta, np.asarray(R("as.numeric(rfitS$beta)"), dtype=float)
        )

    def test_eta(self, setup, R):
        np.testing.assert_array_equal(
            setup.eta, np.asarray(R("as.numeric(rfitS$eta)"), dtype=float)
        )

    def test_sigma2(self, setup, R):
        assert setup.sigma2 == float(R("as.numeric(rfitS$sigma2)")[0])

    def test_method(self, setup):
        assert setup.method == "S"


@needs_robustvarcomp
class TestControl:
    def test_control_defaults_empty(self):
        c = rpm.var_comprob_control()
        assert c.args == {}

    def test_control_translates_names(self):
        c = rpm.var_comprob_control(method="S", cov_init="covOGK", max_it=50)
        assert c.args["method"] == "S"
        assert c.args["cov.init"] == "covOGK"
        assert c.args["max.it"] == 50

    def test_control_unknown_raises(self):
        with pytest.raises(ValueError):
            rpm.var_comprob_control(bogus_arg=1)

    def test_groups_shape_validated(self):
        with pytest.raises(ValueError):
            rpm.var_comprob("y ~ 1", __import__("pandas").DataFrame({"y": [1.0, 2.0]}),
                            groups=np.arange(4), varcov=[np.eye(2)])
