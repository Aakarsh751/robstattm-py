"""Chapter 7, Example 7.2, robust logistic regression on the skin data (Fig 7.5).

Python port of ``skin.R``.

39 observations of vasoconstriction against log volume and log rate of air
inspired. The data are almost perfectly separable, two observations, 4 and 18,
sit on the wrong side of the boundary the other 37 define. Near-separation is
the pathological case for maximum likelihood: coefficients drift toward
infinity to fit those two points, and the resulting fit describes them at the
expense of everything else.

Figure 7.5 plots sorted absolute deviance residuals for weighted Bianco-Yohai
against ML, and observations 4 and 18 are the two that separate the curves.

R packages required: RobStatTM only.
"""
from __future__ import annotations

import numpy as np
from _common import (
    figure,
    ml_deviance_residuals,
    ml_logistic,
    run,
    section,
    table,
)

import robstattm_py as rpm

#: The two observations the book labels in Figure 7.5.
LABELLED = (4, 18)


def main() -> None:
    section("Chapter 7, Example 7.2, skin data")

    skin = rpm.datasets.skin()
    x = skin[["logVOL", "logRATE"]].to_numpy(dtype=float)
    y = skin["vasoconst"].to_numpy(dtype=float)
    print(f"  {len(y)} observations, {int(y.sum())} positive responses")

    ml_coef = ml_logistic(x, y)
    fits = {
        "WML (weighted ML)": rpm.wml_logreg(x, y),
        "BY": rpm.by_logreg(x, y),
        "WBY (weighted BY)": rpm.wby_logreg(x, y),
    }

    section("Coefficients")
    names = ("(Intercept)", "logVOL", "logRATE")
    print(f"\n  {'estimator':<20}" + "".join(f"{n:>14}" for n in names))
    print(f"  {'ML':<20}" + "".join(f"{c:>14.5f}" for c in ml_coef))
    for label, fit in fits.items():
        print(
            f"  {label:<20}"
            + "".join(f"{float(c):>14.5f}" for c in np.asarray(fit.coefficients))
        )
    ratio = abs(float(fits["WBY (weighted BY)"].coefficients[1]) / ml_coef[1])
    print(
        f"\n  The Bianco-Yohai slopes are about {ratio:.1f}x the ML ones, which is\n"
        "  the opposite of what one might expect from 'robust = more\n"
        "  conservative'. It is the right direction here: observations 4 and 18\n"
        "  sit on the wrong side of the boundary the other 37 define, and ML,\n"
        "  which cannot discount any observation, settles on a flatter boundary\n"
        "  that partly accommodates them. Declining to do that makes the fitted\n"
        "  boundary steeper, not shallower."
    )

    section("Figure 7.5, sorted absolute deviance residuals")
    wby = fits["WBY (weighted BY)"]
    wby_dev = np.abs(np.asarray(wby.residual_deviances, dtype=float))
    ml_dev = np.abs(ml_deviance_residuals(x, y, ml_coef))

    table(
        "the two observations the book labels (1-based)",
        {f"obs {i}": (float(wby_dev[i - 1]), float(ml_dev[i - 1])) for i in LABELLED},
    )
    print("  (columns: WBY, ML)")
    table(
        "largest absolute deviance residual",
        {"WBY": float(wby_dev.max()), "ML": float(ml_dev.max())},
    )

    ranked = np.argsort(wby_dev)[::-1][:4] + 1
    table("WBY's four largest, by index (1-based)", {"observations": list(ranked)})
    if set(LABELLED) <= set(int(i) for i in ranked):
        print(
            f"\n  Both of the book's labelled points, {LABELLED[0]} and "
            f"{LABELLED[1]}, are in the robust\n  fit's top four, found rather "
            "than assumed."
        )

    rpm.plot.location_scale(
        rpm.loc_scale_m(wby_dev),
        wby_dev,
        title="Skin, WBY absolute deviance residuals (Figure 7.5)",
        save=figure("ch07_skin_deviances"),
    )


if __name__ == "__main__":
    run(main)
