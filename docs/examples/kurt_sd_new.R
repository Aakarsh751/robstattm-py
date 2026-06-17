data(wine)

# KurtSDNew computes the kurtosis-based projection directions used internally
# to initialise robust covariance and PCA estimators.
set.seed(42)
res <- KurtSDNew(as.matrix(wine))

str(res)
