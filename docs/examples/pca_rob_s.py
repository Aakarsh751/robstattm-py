import robstattm_py as rpm

bus = rpm.datasets.bus()         # 218 buses, 18 shape features

# Robust principal components via spherical/S-estimation, resistant to the
# outlying vehicles that would distort a classical PCA.
rpm.set_seed(42)
res = rpm.pca_rob_s(bus, ncomp=3)   # extract the first 3 robust components
print(res)
