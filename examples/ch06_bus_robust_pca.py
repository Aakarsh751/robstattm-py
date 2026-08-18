"""Chapter 6, Example 6.4, robust PCA on the bus data (Figure 6.10, Table 6.6).

Python port of ``bus.R``.

218 images of buses described by 18 shape features. Column 9 is dropped (it is
constant on this sample, so it carries no information and would divide by a zero
MAD), and the rest are standardised by median and MAD rather than mean and
standard deviation, the scaling step has to be robust too, or the outliers
re-enter through the back door.

Three components are then extracted classically and with ``pcaRobS``, and each
observation's squared reconstruction error is recorded. Table 6.6 compares the
deciles of those two error distributions: the classical fit spreads its error
across every observation to accommodate a few, while the robust fit keeps the
error small for the bulk and large for the outliers, which is what makes the
outliers findable.

R packages required: RobStatTM only.
"""
from __future__ import annotations

import numpy as np
from _common import figure, run, section, table

import robstattm_py as rpm

N_COMPONENTS = 3
#: 1-based column the R script drops.
DROP_COLUMN = 9


def main() -> None:
    section("Chapter 6, Example 6.4, bus data, classical vs robust PCA")

    bus = rpm.datasets.bus()
    kept = [c for i, c in enumerate(bus.columns, start=1) if i != DROP_COLUMN]
    raw = bus[kept].to_numpy(dtype=float)

    # Robust standardisation: median and MAD, matching bus.R.
    centre = np.median(raw, axis=0)
    mad = np.median(np.abs(raw - centre), axis=0) * 1.4826
    x = (raw - centre) / mad
    n, p = x.shape
    print(f"  {n} observations, {p} features (column {DROP_COLUMN} dropped)")

    # Classical PCA by SVD of the centred matrix.
    centred = x - x.mean(axis=0)
    _, singular, vt = np.linalg.svd(centred, full_matrices=False)
    loadings = vt[:N_COMPONENTS].T
    classical_fit = centred @ loadings @ loadings.T
    classical_err = np.sum((centred - classical_fit) ** 2, axis=1)
    explained = np.cumsum(singular**2) / np.sum(singular**2)

    # Robust PCA.
    rob = rpm.pca_rob_s(x, ncomp=N_COMPONENTS)
    robust_err = np.sum((x - np.asarray(rob.fit, dtype=float)) ** 2, axis=1)

    section("Proportion of variance explained by three components")
    table(
        "cumulative",
        {
            "classical": float(explained[N_COMPONENTS - 1]),
            "pcaRobS (propex)": float(rob.propex),
        },
    )

    section("Table 6.6, deciles of the squared reconstruction error")
    alphas = np.arange(0.1, 0.95, 0.1)
    print(f"\n  {'decile':<10}{'classical':>14}{'robust':>14}")
    for a in alphas:
        print(
            f"  {a:<10.1f}{np.quantile(classical_err, a):>14.4f}"
            f"{np.quantile(robust_err, a):>14.4f}"
        )

    print(
        "\n  Read the low deciles. The robust fit reconstructs the bulk of the\n"
        "  data more accurately than the classical one does, despite using the\n"
        "  same number of components, because it did not spend them describing\n"
        "  the outliers."
    )

    section("Figure 6.10, the observations the robust fit cannot reconstruct")
    worst = np.argsort(robust_err)[::-1][:10]
    table(
        "largest robust reconstruction error (1-based index)",
        {
            str(int(i) + 1): (float(robust_err[i]), float(classical_err[i]))
            for i in worst
        },
    )
    print("  (columns: robust error, classical error)")

    rpm.plot.scree(rob, title="Bus, robust PCA scree (Example 6.4)",
                   save=figure("ch06_bus_scree"))


if __name__ == "__main__":
    run(main)
