import robstattm_py as rpm

# Concentration of zinc in 53 mineral samples (some are gross outliers).
zinc = rpm.datasets.mineral()["zinc"].to_numpy()

# The M-scale is a robust measure of spread. Unlike the standard deviation,
# a handful of outliers barely move it.
robust = rpm.m_scale(zinc)
classical = zinc.std(ddof=1)

print(f"robust M-scale     : {robust:.4f}")
print(f"classical std dev  : {classical:.4f}")
print(f"the SD is inflated by the outliers ({classical / robust:.1f}x larger)")
