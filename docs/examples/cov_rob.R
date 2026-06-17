data(wine)                  # 59 wines, 13 chemical measurements

# covRob auto-selects a robust covariance estimator (MM for low dimension,
# Rocke for high) based on the data shape. It uses random projections
# internally, so set.seed() makes the result reproducible (and match Python).
set.seed(42)
fit <- covRob(wine)

print(dim(fit$cov))
print(round(fit$center, 2))
