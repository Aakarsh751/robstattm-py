import robstattm_py as rpm

mineral = rpm.datasets.mineral()

# A control object bundles the tuning knobs for lmrobdet_mm / lmrobdet_dcml.
# Here: switch the loss family and lower the target efficiency.
ctrl = rpm.lmrobdet_control(family="bisquare", efficiency=0.85)
print(ctrl)

fit = rpm.lmrobdet_mm("zinc ~ copper", data=mineral, control=ctrl)
print("coefficients:", fit.coefficients.round(4))
