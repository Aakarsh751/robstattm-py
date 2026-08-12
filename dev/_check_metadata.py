"""Show — and optionally assert — the licence metadata of a built wheel.

    python dev/_check_metadata.py [dist_dir] [--assert]

Package metadata is immutable once a version is on PyPI, so it is worth reading
the actual bytes before publishing rather than trusting the build log. Run
without ``--assert`` to inspect; ``release.yml`` runs it with ``--assert`` so a
regression fails the build instead of shipping.

What is checked, and why each matters:

``License-Expression``
    The PEP 639 form. The older free-text ``License:`` field and the
    ``License :: OSI Approved ::`` classifier are deprecated, and setuptools
    drops them on 2027-02-18. Neither is fatal today, but both are baked into
    every release that carries them.

``License-File`` includes ``NOTICE.md``
    NOTICE.md is what explains that R (GPL-2) and RobStatTM (GPL-3) are
    downloaded at setup time and never redistributed. A wheel that omits it
    ships the MIT grant without the context that makes it accurate.
"""
from __future__ import annotations

import email
import sys
import zipfile
from pathlib import Path

EXPECTED_LICENSE = "MIT"
EXPECTED_LICENSE_FILES = {"LICENSE", "NOTICE.md"}


def main(argv: list[str]) -> int:
    flags = [a for a in argv[1:] if a.startswith("--")]
    positional = [a for a in argv[1:] if not a.startswith("--")]
    strict = "--assert" in flags
    dist_dir = Path(positional[0] if positional else "dist")

    wheels = sorted(dist_dir.glob("*.whl"))
    if not wheels:
        print(f"no wheel found in {dist_dir}/", file=sys.stderr)
        return 1
    wheel = wheels[0]

    with zipfile.ZipFile(wheel) as z:
        metadata_name = next(n for n in z.namelist() if n.endswith(".dist-info/METADATA"))
        meta = email.message_from_string(z.read(metadata_name).decode("utf-8"))
        carried = [n for n in z.namelist() if ".dist-info/licenses/" in n]

    expression = meta.get("License-Expression")
    declared = meta.get_all("License-File") or []
    classifiers = meta.get_all("Classifier") or []
    legacy_field = meta.get("License")
    legacy_classifiers = [c for c in classifiers if c.startswith("License ::")]

    print(f"wheel                {wheel.name}")
    print(f"Metadata-Version     {meta.get('Metadata-Version')}")
    print(f"License-Expression   {expression}")
    print(f"License-File         {declared}")
    print(f"carried in wheel     {[Path(n).name for n in carried]}")
    print(f"legacy License field {legacy_field!r}")
    print(f"legacy classifiers   {legacy_classifiers}")

    problems: list[str] = []
    if expression != EXPECTED_LICENSE:
        problems.append(
            f"License-Expression is {expression!r}, expected {EXPECTED_LICENSE!r}"
        )
    missing = EXPECTED_LICENSE_FILES - set(declared)
    if missing:
        problems.append(f"License-File does not declare {sorted(missing)}")
    not_carried = EXPECTED_LICENSE_FILES - {Path(n).name for n in carried}
    if not_carried:
        problems.append(f"declared but absent from the wheel: {sorted(not_carried)}")
    if legacy_field is not None:
        problems.append("deprecated free-text `License:` field is set")
    if legacy_classifiers:
        problems.append(f"deprecated licence classifiers present: {legacy_classifiers}")

    if not problems:
        print("\nOK")
        return 0

    print("\nlicence metadata problems:", file=sys.stderr)
    for problem in problems:
        print(f"  - {problem}", file=sys.stderr)
    return 1 if strict else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
