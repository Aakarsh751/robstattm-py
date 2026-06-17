import numpy as np

import robstatm_py as rpm

rng = np.random.default_rng(0)
X = rng.standard_normal(60)[:, None]
y = (X.ravel() + 0.5 * rng.standard_normal(60) > 0).astype(int)

# Weighted maximum-likelihood logistic regression — a robust ML variant that
# also reports a coefficient covariance matrix.
fit = rpm.wml_logreg(X, y)
print("coefficients      :", fit.coefficients.round(4))
print("standard deviation:", fit.standard_deviation.round(4))
