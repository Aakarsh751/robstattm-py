data(wine)

# fastmve computes the Minimum Volume Ellipsoid (MVE) estimator of location
# and scatter, a fast resampling-based robust starting point.
set.seed(11)
res <- fastmve(as.matrix(wine))

print(round(res$center, 2))
