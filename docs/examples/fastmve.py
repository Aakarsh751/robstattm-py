import robstattm_py as rpm

wine = rpm.datasets.wine()

# fastmve computes the Minimum Volume Ellipsoid (MVE) estimator of location
# and scatter, a fast resampling-based robust starting point.
rpm.set_seed(11)
res = rpm.fastmve(wine)
print(res)
