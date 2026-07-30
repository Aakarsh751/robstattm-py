#!/usr/bin/env python
"""Interactive playground — run individual exploration workflows without pytest.

Usage (from repo root)::

    python exploration/run_playground.py --list
    python exploration/run_playground.py mineral
    python exploration/run_playground.py algae bisquare-sweep
    python exploration/run_playground.py all

Each scenario prints a short summary. Requires R + RobStatTM (see ``rpm.check_setup()``).
"""
from __future__ import annotations

import argparse
import sys
from typing import Callable

import robstattm_py as rpm

BOOK = rpm.lmrobdet_control(bb=0.5, efficiency=0.85, family="bisquare")


def _header(name: str) -> None:
    print(f"\n{'=' * 60}\n  {name}\n{'=' * 60}")


def mineral() -> None:
    _header("mineral — flagship MM regression")
    df = rpm.datasets.mineral()
    fit = rpm.lmrobdet_mm("zinc ~ copper", data=df)
    print(fit)
    print(fit.summary())


def algae() -> None:
    _header("algae — dot formula (Example 5.4)")
    df = rpm.datasets.algae()
    fit = rpm.lmrobdet_mm("V12 ~ .", data=df, control=BOOK)
    print(f"scale={fit.scale:.4f}  rank={fit.rank}  R²={fit.r_squared:.4f}")


def shock() -> None:
    _header("shock — M regression (Example 4.1)")
    df = rpm.datasets.shock()
    ctrl = rpm.lmrobm_control(bb=0.5, efficiency=0.85, family="bisquare")
    fit = rpm.lmrob_m("time ~ n.shocks", data=df, control=ctrl)
    print(f"scale={fit.scale:.4f}  converged={fit.converged}")


def stackloss_step() -> None:
    _header("stackloss — stepwise RFPE")
    df = rpm.datasets.stackloss()
    full = rpm.lmrobdet_mm(
        "stack.loss ~ Air.Flow + Water.Temp + Acid.Conc.", data=df
    )
    step = rpm.step_lmrobdet(full)
    print(f"start:  {full.formula}")
    print(f"final:  {step.final_formula}")
    print(f"RFPE trace ({len(step.anova_rfpe)} steps): {step.anova_rfpe.round(3)}")


def wine_cov() -> None:
    _header("wine — robust vs classical covariance")
    rpm.set_seed(42)
    X = rpm.datasets.wine().to_numpy()
    rob = rpm.cov_rob_mm(X)
    cla = rpm.cov_classic(X)
    print(f"robust center[:3]   = {rob.center[:3].round(3)}")
    print(f"classical center[:3]= {cla.center[:3].round(3)}")


def bus_pca() -> None:
    _header("bus — prcomp_rob with rank=5")
    rpm.set_seed(42)
    pc = rpm.prcomp_rob(rpm.datasets.bus().to_numpy(), rank=5)
    print(f"sdev[:5] = {pc.sdev[:5].round(3)}")
    print(pc.summary())


def skin_glm() -> None:
    _header("skin — BY / WBY / WML logistic")
    df = rpm.datasets.skin()
    X = df[["logVOL", "logRATE"]].to_numpy(float)
    y = df["vasoconst"].to_numpy(float)
    for name, fn in [
        ("BY", rpm.by_logreg),
        ("WBY", rpm.wby_logreg),
        ("WML", rpm.wml_logreg),
    ]:
        fit = fn(X, y)
        print(f"{name}: coef={fit.coefficients.round(3)}  converged={fit.converged}")


def bisquare_sweep() -> None:
    _header("mineral — ψ-family sweep @ 85% efficiency")
    df = rpm.datasets.mineral()
    for fam in ("mopt", "bisquare", "huber", "opt"):
        fit = rpm.lmrobdet_mm(
            "zinc ~ copper", data=df, family=fam, efficiency=0.85
        )
        print(f"  {fam:8s}  scale={fit.scale:.4f}  iter={fit.iter}")


def dcml() -> None:
    _header("mineral — DCML regression")
    fit = rpm.lmrobdet_dcml("zinc ~ copper", data=rpm.datasets.mineral())
    print(f"scale={fit.scale:.4f}  converged={fit.converged}")


def coleman() -> None:
    _header("coleman — cross-package dataset + dot formula")
    df = rpm.datasets.load("robustbase", "coleman")
    fit = rpm.lmrobdet_mm("Y ~ .", data=df)
    print(fit)


SCENARIOS: dict[str, Callable[[], None]] = {
    "mineral": mineral,
    "algae": algae,
    "shock": shock,
    "stackloss-step": stackloss_step,
    "wine-cov": wine_cov,
    "bus-pca": bus_pca,
    "skin-glm": skin_glm,
    "bisquare-sweep": bisquare_sweep,
    "dcml": dcml,
    "coleman": coleman,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scenarios",
        nargs="*",
        help=f"One of: {', '.join(SCENARIOS)} — or 'all'",
    )
    parser.add_argument("--list", action="store_true", help="List scenario names")
    args = parser.parse_args(argv)

    if args.list:
        for k in SCENARIOS:
            print(k)
        return 0

    names = args.scenarios or ["mineral"]
    if "all" in names:
        names = list(SCENARIOS)

    rpm.check_setup()
    rpm.set_seed(42)

    for name in names:
        if name not in SCENARIOS:
            print(f"Unknown scenario: {name!r}. Use --list.", file=sys.stderr)
            return 1
        SCENARIOS[name]()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
