# Conda-forge packaging

This folder holds a draft [conda-forge](https://conda-forge.org/) recipe
(`meta.yaml`) for `robstattm-py`. Conda-forge is worth having because it ships
prebuilt `rpy2` **and** R, so a conda user gets a working robust-statistics
stack with a single `conda install` and no compiler, no CRAN step, and no
`robstattm-py setup`.

## Status

The recipe is not submitted yet. It cannot be until the package is on PyPI,
because conda-forge builds from the published source tarball (`sdist`).

## How to submit (after the first PyPI release)

1. Publish `robstattm-py` to PyPI (see `docs/RELEASING.md`).
2. Get the sdist hash:
   ```bash
   pip download robstattm-py --no-deps --no-binary :all: -d /tmp/rp
   openssl sha256 /tmp/rp/robstattm_py-*.tar.gz
   ```
   Paste it into `source.sha256` in `meta.yaml`.
3. Confirm each R run-dependency has a conda-forge build on the platforms you
   want (linux-64, osx-64, osx-arm64, win-64). The one to check is **r-pyinit**;
   if it is missing on a platform, either add it to the recipe once available or
   note that estimators needing pyinit are unavailable there. `r-robstattm`,
   `r-robustbase`, and `r-rrcov` are already on conda-forge.
4. Fork [conda-forge/staged-recipes](https://github.com/conda-forge/staged-recipes),
   add this file as `recipes/robstattm-py/meta.yaml`, and open a PR. The
   conda-forge bot lints it and builds on all platforms in the PR.
5. Once merged, conda-forge creates `robstattm-py-feedstock`. After that,
   releases are picked up automatically by the version bot; you only review the
   PRs it opens.

## Local check before submitting

```bash
conda install -n base conda-build conda-smithy
conda build packaging/conda
```

This does a real build and runs the import smoke test from the recipe.
