import robstattm_py as rpm

wine = rpm.datasets.wine()

# The classical (non-robust) mean and covariance — handy as a baseline to
# compare against the robust estimators (cov_rob_mm, cov_rob_rocke).
fit = rpm.cov_classic(wine)

print("covariance shape :", fit.cov.shape)
print(fit.summary())             # eigenvalues of the covariance matrix
