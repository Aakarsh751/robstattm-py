import robstattm_py as rpm

# Zinc concentration in 53 mineral samples (some are gross outliers).
zinc = rpm.datasets.mineral()["zinc"].to_numpy()

# Robust M-estimators of location AND scale, in one call.
est = rpm.loc_scale_m(zinc, psi="bisquare", eff=0.95)

print(f"robust location: {est.mu:.4f}")
print(f"robust scale:    {est.disper:.4f}")
print(f"std-err of mu:   {est.std_mu:.4f}")
print()
print(f"compare classical: mean={zinc.mean():.4f}   std={zinc.std(ddof=1):.4f}")
print("(the classical mean/std are pulled by the outlying samples)")
