import robstatm_py as rpm

mineral = rpm.datasets.mineral()

# Control object for the M-estimator lmrob_m: choose the loss family,
# efficiency, and the breakdown tuning constant `bb`.
ctrl = rpm.lmrobm_control(efficiency=0.85, family="bisquare", bb=0.5)
print(ctrl)

fit = rpm.lmrob_m("zinc ~ copper", data=mineral, control=ctrl)
print("coefficients:", fit.coefficients.round(4))
