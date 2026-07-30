import robstattm_py as rpm

wine = rpm.datasets.wine()

# Rocke's S-estimator of multivariate location and scatter — designed to stay
# efficient in higher dimensions where other robust estimators lose power.
rpm.set_seed(42)
fit = rpm.cov_rob_rocke(wine)

print("covariance shape :", fit.cov.shape)
print("robust center    :", fit.center.round(2))
# Mahalanobis distances flag the outlying wines.
print("largest distances:", fit.dist.round(1)[fit.dist.argsort()[-5:]])
