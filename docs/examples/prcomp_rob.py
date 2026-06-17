import robstatm_py as rpm

# Bus silhouettes — 218 obs, 18 image-shape features.
bus = rpm.datasets.bus()

# Robust principal-components decomposition.
pc = rpm.prcomp_rob(bus.to_numpy())

print(f"top-5 robust std-devs:  {pc.sdev[:5].round(3)}")
print(f"variance explained by PC1-PC3: "
      f"{(pc.sdev[:3] ** 2 / (pc.sdev ** 2).sum() * 100).round(1)} %")
print(f"rotation shape: {pc.rotation.shape}   scores shape: {pc.scores.shape}")
