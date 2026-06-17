data(wine)                  # 59 obs of 13 chemical measurements
X <- as.matrix(wine)

# Robust MM-covariance estimator (stochastic initial subsampling -> set.seed).
set.seed(42)
fit <- covRobMM(X)

print(round(fit$center[1:5], 3))
print(round(diag(fit$cov)[1:5], 2))
