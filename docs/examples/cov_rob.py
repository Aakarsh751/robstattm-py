import robstattm_py as rpm

wine = rpm.datasets.wine()       # 59 wines, 13 chemical measurements

# cov_rob is the convenient entry point: it auto-selects a robust covariance
# estimator (MM for low dimension, Rocke for high) based on the data shape.
rpm.set_seed(42)
fit = rpm.cov_rob(wine)

print("estimator chosen :", fit.estimator_type)
print("covariance shape :", fit.cov.shape)
print("robust center    :", fit.center.round(2))
