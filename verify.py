"""Top-level verification harness — answers the question
'how do I test everything and verify all outputs against R?'

Usage::

    python verify.py              # full check (~ 30s)
    python verify.py --quick      # smoke check (~ 5s)
    python verify.py --coverage   # print the R↔Python coverage matrix
    python verify.py --help-all   # print the full wrapper inventory

The harness is *not* a replacement for the pytest suite — it's a fast,
human-readable confidence check you can run before showing the project
to a reviewer.
"""
from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
import time



def banner(msg: str) -> None:
    print("\n" + "=" * 78)
    print(msg)
    print("=" * 78)


def section(msg: str) -> None:
    print(f"\n--- {msg} ---")


def check(label: str, ok: bool, detail: str = "") -> bool:
    mark = "[OK] " if ok else "[FAIL]"
    print(f"  {mark} {label}" + (f"  ({detail})" if detail else ""))
    return ok


def run_smoke() -> int:
    """Quick: every wrapper family runs end-to-end without crashing."""
    import numpy as np
    import robstattm_py as rpm

    banner("SMOKE — every wrapper family runs end-to-end")
    failures = 0
    df = rpm.datasets.mineral()
    wine = rpm.datasets.wine()
    rpm.set_seed(42)

    section("Univariate")
    failures += not check("loc_scale_m",
                          rpm.loc_scale_m(df["zinc"].to_numpy()).mu > 0)
    failures += not check("m_scale",
                          rpm.m_scale(df["zinc"].to_numpy()) > 0)

    section("Regression")
    fit_mm = rpm.lmrobdet_mm("zinc ~ copper", data=df)
    failures += not check("lmrobdet_mm", fit_mm.coefficients.shape == (2,),
                          f"coef={fit_mm.coefficients}")
    fit_dcml = rpm.lmrobdet_dcml("zinc ~ copper", data=df)
    failures += not check("lmrobdet_dcml", fit_dcml.coefficients.shape == (2,))
    fit_m = rpm.lmrob_m("zinc ~ copper", data=df)
    failures += not check("lmrob_m", fit_m.coefficients.shape == (2,))
    py = rpm.pyinit(X=df[["copper"]].to_numpy(),
                    y=df["zinc"].to_numpy())
    failures += not check("pyinit", py.coefficients.ndim == 2,
                          f"k_candidates={py.coefficients.shape[1]}")
    rfpe = fit_mm.rfpe()
    failures += not check("lmrobdetMM.RFPE method", rfpe > 0,
                          f"RFPE={rfpe:.4g}")

    section("Covariance / PCA")
    cov_c = rpm.cov_classic(wine)
    failures += not check("cov_classic", cov_c.cov.shape == (13, 13))
    rpm.set_seed(42)
    cov_mm = rpm.cov_rob_mm(wine)
    failures += not check("cov_rob_mm", cov_mm.cov.shape == (13, 13))
    rpm.set_seed(42)
    prc = rpm.prcomp_rob(wine)
    failures += not check("prcomp_rob", prc.sdev.shape == (13,))

    section("GLM")
    rng = np.random.default_rng(0)
    x = rng.standard_normal(60)[:, None]
    y = (x.ravel() + 0.5 * rng.standard_normal(60) > 0).astype(int)
    lg = rpm.by_logreg(X=x, y=y)
    failures += not check("by_logreg", lg.converged)

    section("Plotting (Path A R-graphics)")
    p = rpm.plotting.r_plot(
        "plot(zinc ~ copper, data=mineral, pch=19)",
        path="verify_smoke_plot.png", dpi=72, width=4, height=3,
    )
    failures += not check("r_plot", p.exists() and p.stat().st_size > 0)

    section("Ergonomics (UI doc §6)")
    failures += not check("fit.to_dict()", isinstance(fit_mm.to_dict(), dict))
    failures += not check("fit.coef_df()", fit_mm.coef_df().shape == (2,))
    failures += not check("fit._repr_html_()", len(fit_mm._repr_html_()) > 100)
    failures += not check("fit.to_r()", fit_mm.to_r() is not None)

    section("Performance (UI doc §11)")
    failures += not check("r_started", rpm.r_started())
    t = rpm.bench.timer(lambda: rpm.lmrobdet_mm("zinc ~ copper", data=df))
    failures += not check("bench.timer", t.total_seconds > 0,
                          f"{t.total_seconds*1000:.1f} ms")

    section("(X, y) array form (UI doc §3)")
    fit_xy = rpm.lmrobdet_mm(X=df[["copper"]], y=df["zinc"])
    failures += not check("X,y == formula",
                          np.array_equal(fit_xy.coefficients, fit_mm.coefficients))

    section("R-name aliases (UI doc §2.3)")
    from robstattm_py.compat_r import lmrobdetMM, covRobMM, BYlogreg
    failures += not check("compat_r.lmrobdetMM", lmrobdetMM is rpm.lmrobdet_mm)
    failures += not check("compat_r.covRobMM", covRobMM is rpm.cov_rob_mm)

    banner(f"SMOKE RESULT: {failures} failure(s)" if failures
           else "SMOKE RESULT: all green")
    return failures


def run_pytest() -> int:
    """Run the full pytest suite and report."""
    banner("PYTEST — full strict-tier suite (atol=0, rtol=0 vs R)")
    cmd = [
        sys.executable, "-m", "pytest", "tests/", "-q", "--tb=line",
        "--ignore=tests/_smoke_check.py",
        "--ignore=tests/_smoke_dcml.py",
        "--ignore=tests/_smoke_lmrobdet.py",
        "--ignore=tests/_smoke_step_rlt.py",
        "--ignore=tests/_smoke_ergonomics.py",
        "--ignore=tests/_smoke_ui_phase2.py",
        "--ignore=tests/_ui_demo.py",
    ]
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t0
    print(proc.stdout[-2000:])
    if proc.stderr:
        print("STDERR (last 500 chars):", proc.stderr[-500:])
    print(f"\npytest finished in {dt:.1f}s (returncode {proc.returncode})")
    return proc.returncode


def print_coverage() -> int:
    """Display the R↔Python coverage matrix."""
    banner("COVERAGE — see docs/coverage_matrix.md for the full table")
    from pathlib import Path
    p = Path("docs/coverage_matrix.md")
    if p.exists():
        print(p.read_text(encoding="utf-8"))
    else:
        print("(missing — run from project root)")
    return 0


def print_help_all() -> int:
    """Print docstring of every wrapper for the reviewer."""
    import robstattm_py as rpm
    banner("FULL WRAPPER INVENTORY")
    names = sorted(rpm.list_names().values())
    seen: set[str] = set()
    for n in names:
        if n in seen:
            continue
        seen.add(n)
        try:
            rpm.help(n)
        except Exception as e:
            print(f"\n{n}: (help failed: {e})")
        print()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--quick", action="store_true", help="smoke only (~5s)")
    g.add_argument("--full", action="store_true", help="smoke + pytest (default)")
    g.add_argument("--coverage", action="store_true", help="print coverage matrix")
    g.add_argument("--help-all", action="store_true",
                   help="print docstring of every wrapper")
    args = ap.parse_args()

    if args.coverage:
        return print_coverage()
    if args.help_all:
        return print_help_all()
    if args.quick:
        return run_smoke()
    # default = full
    rc = run_smoke()
    if rc:
        print("\nSmoke failed; skipping pytest.")
        return rc
    rc = run_pytest()
    return rc


if __name__ == "__main__":
    sys.exit(main())
