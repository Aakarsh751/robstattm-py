import numpy as np
import robstattm_py as rpm

# Italian wine cultivar — 59 obs of 13 chemical measurements.
wine = rpm.datasets.wine()
X = wine.to_numpy()

# Robust MM-covariance estimator (stochastic initial subsampling -> set_seed).
rpm.set_seed(42)
fit = rpm.cov_rob_mm(X)

print(f"robust center (first 5 vars):  {fit.center[:5].round(3)}")
print(f"robust covariance diag:        {np.diag(fit.cov)[:5].round(2)}")
print(f"# obs flagged as outliers:     {int((fit.dist > np.quantile(fit.dist, 0.95)).sum())}")
