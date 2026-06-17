import numpy as np
import robstatm_py as rpm

rng = np.random.default_rng(42)
x = np.concatenate([rng.normal(size=95), rng.normal(20, 1, size=5)])  # 5% outliers

# Robust M-estimators of location and scale.
est = rpm.loc_scale_m(x, psi="bisquare", eff=0.95)

print(f"robust location: {est.mu:.4f}")
print(f"robust scale:    {est.disper:.4f}")
print(f"std-err of mu:   {est.std_mu:.4f}")
print()
print(f"compare classical: mean={x.mean():.4f}   std={x.std(ddof=1):.4f}")
print("(classical estimates are pulled hard by the 5 outliers at ~20)")
