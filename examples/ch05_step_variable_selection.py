"""Chapter 5, Example 5.3 — robust variable selection by RFPE (Table 5.2).

Python port of ``step.R``.

Six candidate predictors, of which only the first three carry signal
(``beta = (1, 1, 1, 0, 0, 0)``), and six of the fifty observations have been
turned into outliers with a matching pattern planted in the three *noise*
columns. Classical stepwise selection follows that planted pattern and keeps the
useless variables; ``step.lmrobdetMM``, which drops terms by robust final
prediction error rather than by AIC, does not.

``step.R`` carries a note worth repeating: the sequence of models in Table 5.2
of the book is right, but the RFPE values printed there are wrong. The ones
computed here are the correct ones.

The design matrix is generated from R's RNG under ``set.seed(300)``, matching
the R script, so these numbers are directly comparable with it.

R packages required: RobStatTM only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from _common import figure, run, section, table

import robstattm_py as rpm

SEED = 300
N = 50
P = 6
BETA = np.array([1.0, 1.0, 1.0, 0.0, 0.0, 0.0])
N_OUTLIERS = 6


def simulate() -> pd.DataFrame:
    """Reproduce ``step.R``'s data set from R's RNG under its seed."""
    rpm.set_seed(SEED)
    from robstattm_py._r import r

    ro = r()
    # R fills a matrix column-major; order="F" reproduces that layout, and
    # getting it wrong would quietly give a different (but plausible) data set.
    x = np.asarray(ro.r(f"rnorm({N * P})"), dtype=float).reshape((N, P), order="F")
    noise = np.asarray(ro.r(f"rnorm({N})"), dtype=float)
    y = x @ BETA + 1.0 + noise

    # Six gross outliers in y, with a matching ramp planted in the three noise
    # columns — so a non-robust criterion is actively tempted to keep them.
    y[:N_OUTLIERS] = np.arange(30, 30 + 5 * N_OUTLIERS, 5, dtype=float)
    for i in range(N_OUTLIERS):
        x[i, 3:] = (i + 1) / 2

    data = pd.DataFrame(x, columns=[f"V{i + 2}" for i in range(P)])
    data.insert(0, "y", y)
    return data


def main() -> None:
    section("Chapter 5, Example 5.3 — robust stepwise selection")

    data = simulate()
    signal = [c for c, b in zip(data.columns[1:], BETA, strict=True) if b != 0]
    noise = [c for c, b in zip(data.columns[1:], BETA, strict=True) if b == 0]
    print(f"  true signal: {', '.join(signal)}")
    print(f"  pure noise (but correlated with the planted outliers): {', '.join(noise)}")

    cont = rpm.lmrobdet_control(bb=0.5, efficiency=0.85, family="bisquare")
    full = rpm.lmrobdet_mm("y ~ .", data=data, control=cont)

    section("Full model")
    print(full.summary())

    section("Table 5.2 — backward elimination by RFPE")
    result = rpm.step_lmrobdet(full, direction="backward")
    print(f"  selected model: {result.final_formula}")
    print(f"  robust scale of the selected fit: {result.scale:.4f}")
    table(
        "RFPE at each step (lower is better)",
        {f"step {i}": float(v) for i, v in enumerate(result.anova_rfpe)},
    )

    kept = [n for n in result.coef_names if n != "(Intercept)"]
    table(
        "outcome",
        {
            "terms kept": kept,
            "true signal recovered": sorted(set(kept) & set(signal)),
            "noise wrongly kept": sorted(set(kept) & set(noise)),
        },
    )
    if set(kept) == set(signal):
        print("\n  Exactly the three real predictors — the planted pattern did not fool it.")

    rpm.plot.diagnostics(
        full,
        title="Stepwise example — full-model diagnostics",
        save=figure("ch05_step_diagnostics"),
    )


if __name__ == "__main__":
    run(main)
