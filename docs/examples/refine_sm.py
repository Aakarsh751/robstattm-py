import numpy as np

import robstattm_py as rpm

# Build a tiny linear dataset: y = 1 + 2*x + noise.
rng = np.random.default_rng(0)
x = rng.standard_normal(50)
X = np.column_stack([np.ones(50), x])
y = X @ np.array([1.0, 2.0]) + rng.standard_normal(50)

# refine_sm runs refinement (reweighting) iterations of an S-estimator,
# starting from an initial beta and scale.
res = rpm.refine_sm(
    X, y,
    initial_beta=[0.9, 1.9], initial_scale=0.5,
    b=0.5, cc=1.54764, family="bisquare", tol=1e-7,
)
print("refined beta :", np.round(res.beta, 4))
print("refined scale:", round(res.scale, 4))
print("converged    :", res.converged, "in", res.iterations, "iterations")
