"""``rpm.help(name)``, single help lookup that accepts either the
R-original name or the Python (snake_case) name.

Per ``dev/design/user_interface.md §9``.
"""
from __future__ import annotations

import inspect
import textwrap
from typing import Any

# R-name → Python attribute name. Single source of truth - keep in sync
# with the table in dev/design/user_interface.md §5 and with compat_r.py.
_R_TO_PY: dict[str, str] = {
    # univariate
    "locScaleM": "loc_scale_m", "MLocDis": "loc_scale_m",
    "scaleM": "m_scale", "mscale": "m_scale",
    # regression
    "lmrobM": "lmrob_m",
    "lmrobdetMM": "lmrobdet_mm",
    "lmrobdetDCML": "lmrobdet_dcml",
    "pyinit": "pyinit",
    "INVTR2": "invtr2",
    "step.lmrobdetMM": "step_lmrobdet",
    "rob.linear.test": "rob_linear_test",
    "lsRobTestMM": "rob_linear_test", "lmrobdetLinTest": "rob_linear_test",
    "lmrobM.control": "lmrobm_control",
    "lmrobdet.control": "lmrobdet_control",
    "refine.sm": "refine_sm",
    # covariance
    "covRob": "cov_rob", "Multirobu": "cov_rob",
    "covRobMM": "cov_rob_mm", "MMultiSHR": "cov_rob_mm",
    "covRobRocke": "cov_rob_rocke", "RockeMulti": "cov_rob_rocke",
    "covClassic": "cov_classic",
    "KurtSDNew": "kurt_sd_new", "initPP": "kurt_sd_new",
    "fastmve": "fastmve",
    # pca
    "pcaRobS": "pca_rob_s", "SMPCA": "pca_rob_s",
    "prcompRob": "prcomp_rob",
    # glm
    "BYlogreg": "by_logreg", "logregBY": "by_logreg",
    "WBYlogreg": "wby_logreg", "logregWBY": "wby_logreg",
    "WMLlogreg": "wml_logreg", "logregWML": "wml_logreg",
    # external stretch packages (pense / GSE / TSGS)
    "pense": "pense", "pense_cv": "pense_cv",
    "GSE": "gse", "TSGS": "tsgs",
    # external stretch packages (example-script reproduction, D-024)
    "arima.rob": "arima_rob",
    "varComprob": "var_comprob", "varComprob.control": "var_comprob_control",
    "glmrob": "glmrob",
    "cubinf": "cubinf", "cubinf.control": "cubinf",
    # comparison models (non-RobStatTM baselines) + fit.models facade
    "lm": "lm",
    "glm": "glm",
    "rlm": "rlm",
    "ltsReg": "lts_reg", "lts": "lts_reg",
    "lmrob": "lmrob",
    "fit.models": "compare", "fitModels": "compare",
}


def help(name: str) -> None:
    """Print the docstring for the wrapper identified by ``name``.

    Accepts either the R-original name (``"lmrobdetMM"``,
    ``"covRobMM"``, ``"refine.sm"``) or the canonical Python name
    (``"lmrobdet_mm"``, ``"cov_rob_mm"``, ``"refine_sm"``).

    Examples
    --------
    >>> import robstattm_py as rpm
    >>> rpm.help("lmrobdetMM")    # doctest: +SKIP
    >>> rpm.help("lmrobdet_mm")   # doctest: +SKIP   # same output
    """
    import robstattm_py as rpm

    py_name = _R_TO_PY.get(name, name)
    obj: Any = getattr(rpm, py_name, None)
    if obj is None:
        # Maybe it's something in a submodule (e.g. rpm.psi.bisquare).
        for sub in ("psi", "datasets", "plotting", "external"):
            container = getattr(rpm, sub, None)
            if container is not None:
                obj = getattr(container, py_name, None)
                if obj is not None:
                    break
    if obj is None:
        avail = sorted(set(list(_R_TO_PY) + list(_R_TO_PY.values())))
        raise KeyError(
            f"unknown name {name!r}. Try one of: " + ", ".join(avail[:15])
            + ", ..."
        )

    title = f"{py_name}  (R: {name})" if name != py_name else py_name
    print(title)
    print("=" * len(title))
    print()
    doc = inspect.getdoc(obj) or "(no docstring)"
    print(textwrap.dedent(doc))


def list_names() -> dict[str, str]:
    """Return a copy of the R → Python name map (for docs / discovery)."""
    return dict(_R_TO_PY)
