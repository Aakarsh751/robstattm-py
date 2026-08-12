# Releasing to PyPI

Everything in this repository is already wired for a trusted-publishing release.
What is missing is the one thing that cannot be automated: a person creating the
publisher on PyPI. This page is the whole procedure, in order.

> **Status:** `robstattm-py` is **not yet on PyPI**. Until step 4 completes,
> `pip install robstattm-py` fails with *"No matching distribution found"*, and
> the install docs deliberately say `git clone` instead — see
> [`quality_gates.md`](quality_gates.md) for the list of files to flip back.

---

## Background: what publishing actually involves

Four separate things, often conflated:

| Thing | What it is |
|---|---|
| **The build** | Turning the source tree into a `.whl` (a zip installers can unpack) and a `.tar.gz` (an sdist — the source, for anyone who must rebuild). `python -m build` does both. |
| **The metadata** | Name, version, dependencies, licence, README. Baked into the artifacts at build time and **immutable once published**. |
| **The index** | PyPI. Stores artifacts under a project name that is globally unique and first-come. |
| **The authentication** | How PyPI knows the upload is really from you. Either a long-lived API token, or — better — a short-lived OIDC token issued to a specific GitHub workflow. |

Two facts that shape everything else:

- **A version number can never be reused.** Not after deletion, not after a
  mistake. Yank `0.1.0` and `0.1.0` is gone forever; the fix is `0.1.1`.
- **Metadata cannot be edited after upload.** A typo in the licence field or a
  broken README is permanent for that version. This is why the release workflow
  asserts metadata *before* uploading.

---

## Step 0 — Decide the version

`pyproject.toml` says `version = "0.1.0"`. The release workflow refuses to
publish if the git tag disagrees with it, so change the file first if you want a
different number.

Semantic versioning: `MAJOR.MINOR.PATCH`. Below `1.0.0` the API is understood to
be unstable, which is honest for a first release.

## Step 1 — Confirm the tree is releasable

```bash
python -m pytest tests/ -q            # 1034 passed with notebooks
python -m ruff check src tests exploration examples
python -m sphinx -b html docs docs/_build/html -W
python -m build                       # produces dist/
python -m twine check dist/*
python dev/_check_metadata.py dist --assert
```

The release workflow runs the last three itself, plus a wheel smoke-test in a
clean venv. Running them locally first just shortens the feedback loop.

## Step 2 — Create the TestPyPI publisher (rehearsal)

TestPyPI is a full, separate copy of PyPI for exactly this. Use it: a botched
real release cannot be undone.

1. Register at <https://test.pypi.org/account/register/> and verify the email.
2. Enable 2FA — it is mandatory for uploading.
3. Go to <https://test.pypi.org/manage/account/publishing/> — the **account**
   sidebar, not a project's, because the project does not exist yet. This
   creates a *pending* publisher.
4. Fill in exactly:

   | Field | Value |
   |---|---|
   | PyPI Project Name | `robstattm-py` |
   | Owner | `Aakarsh751` |
   | Repository name | `robstattm-py` |
   | Workflow name | `release.yml` |
   | Environment name | `testpypi` |

   **The environment name must match the workflow exactly.** A mismatch is the
   single most common failure and reports as `invalid-publisher`, which does not
   say which field is wrong.

## Step 3 — Rehearse

Actions → **Release** → *Run workflow* → target `testpypi`.

You do **not** need to create the GitHub environments by hand: "running a
workflow that references an environment that does not exist will create an
environment with the referenced name"
([GitHub docs](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)).
`release.yml` already names `testpypi` and `pypi`, so they appear on first run.
Create them beforehand only if you want protection rules — a required reviewer
on `pypi` is a reasonable thing to add later, since it makes an accidental tag
push unable to publish on its own.

That builds, checks, smoke-tests the wheel, and uploads to TestPyPI. Then
install from it in a fresh environment:

```bash
python -m venv /tmp/rehearsal && /tmp/rehearsal/bin/pip install \
    --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    robstattm-py
```

`--extra-index-url` is required: TestPyPI does not mirror real dependencies, so
numpy and rpy2 must come from the real index.

Check the project page renders: description, licence (should read **MIT**),
links, classifiers.

## Step 4 — Create the real publisher

Same as step 2, on <https://pypi.org/manage/account/publishing/>, with
**Environment name: `pypi`**.

The project name is reserved on first successful publish, not when the pending
publisher is created — so nothing stops someone else taking `robstattm-py` in
between. If that matters, do steps 4 and 5 close together.

## Step 5 — Publish

```bash
git tag v0.1.0
git push origin v0.1.0
```

The tag triggers `release.yml`, which:

1. builds the sdist and wheel;
2. runs `twine check` and the licence-metadata assertion;
3. verifies the tag matches `pyproject.toml`;
4. installs the wheel in a clean venv and confirms it imports **without
   starting R** — proof that R is only needed at call time;
5. publishes to PyPI via OIDC (no token anywhere in this repository);
6. builds and pushes the container image to ghcr.io;
7. creates the GitHub release with the artifacts attached.

## Step 6 — Afterwards

- `pip install robstattm-py` in a fresh venv on a machine that has never seen
  this repo. That is the only real proof.
- **Flip the install docs back** — `docs/quality_gates.md` lists every file
  carrying the temporary `git clone` wording. Grep for `not on PyPI`.
- Move the `[Unreleased]` section of `CHANGELOG.md` under the new version.
- Consider `conda-forge` next: it is a separate ecosystem with its own
  feedstock-PR process, and it is what Linux users generally want because
  conda-forge ships prebuilt `rpy2` and R.

---

## If it fails

| Symptom | Cause |
|---|---|
| `invalid-publisher` | A field mismatch between PyPI and the workflow. Check owner, repo, workflow filename, and above all the **environment name**. |
| `Non-user identities cannot create new projects` | The pending publisher was not created, or was created for a different project name. |
| Workflow has no OIDC token | The job is missing `permissions: id-token: write`. It must be on the *job*, not only the workflow. |
| `File already exists` | That version was already uploaded. Bump the version; it cannot be replaced. |
| README renders as plain text | `twine check` catches this before upload — read its output. |

## Why trusted publishing rather than an API token

A token is a long-lived secret: it lives in repository settings, works from
anywhere, and if it leaks, whoever has it can publish as you until you notice.
Trusted publishing issues a token that lasts minutes, is scoped to one workflow
in one repository, and is minted only for a run that GitHub itself vouches for.
There is nothing in this repository to steal.

## Sources

- [Packaging Python Projects](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
- [PyPI: Publishing with a Trusted Publisher](https://docs.pypi.org/trusted-publishers/)
- [PyPI: Creating a project through OIDC](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
- [PyPI: Trusted publishing troubleshooting](https://docs.pypi.org/trusted-publishers/troubleshooting/)
- [PEP 639 licence declaration](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license)
