import robstattm_py as rpm

wine = rpm.datasets.wine()

# KurtSDNew computes the kurtosis-based projection directions used internally
# to initialise robust covariance and PCA estimators.
rpm.set_seed(42)
res = rpm.kurt_sd_new(wine)
print(res)
