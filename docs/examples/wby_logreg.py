import numpy as np

import robstatm_py as rpm

# Simulate a binary-outcome dataset.
rng = np.random.default_rng(0)
X = rng.standard_normal(60)[:, None]
y = (X.ravel() + 0.5 * rng.standard_normal(60) > 0).astype(int)

# Weighted Bianco-Yohai estimator: a robust logistic regression that
# downweights leverage points in the predictor space.
fit = rpm.wby_logreg(X, y)
print("coefficients      :", fit.coefficients.round(4))
print("standard deviation:", fit.standard_deviation.round(4))
