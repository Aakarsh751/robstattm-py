"""Print the License field of each R package this project touches.

Read from the installed DESCRIPTION files, which is what is actually in use
here, rather than from a web page that may describe a different version.
NOTICE.md ships inside the wheel, so these strings have to be right.
"""
from __future__ import annotations

from robstattm_py._r import r

PACKAGES = [
    "RobStatTM", "pyinit", "robustbase", "rrcov", "robust",
    "pense", "GSE", "robustarima", "robustvarComp", "robcbi", "robeth",
    "WWGbook", "quantreg", "nlme",
]

ro = r()
print(f"{'package':<16} {'version':<10} License")
print("-" * 72)
for pkg in PACKAGES:
    installed = bool(ro.r(f"isTRUE(requireNamespace('{pkg}', quietly=TRUE))")[0])
    if not installed:
        print(f"{pkg:<16} {'-':<10} (not installed)")
        continue
    version = str(ro.r(f"as.character(packageVersion('{pkg}'))")[0])
    licence = str(ro.r(f"packageDescription('{pkg}')$License")[0])
    print(f"{pkg:<16} {version:<10} {licence}")

print()
print("R itself:", str(ro.r("R.version.string")[0]))
print("R license:", str(ro.r("paste(readLines(file.path(R.home('doc'), 'COPYING'))[1:3], collapse=' | ')")[0])[:120])
