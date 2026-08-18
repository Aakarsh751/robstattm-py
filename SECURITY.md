# Security policy

## Supported versions

The latest release on PyPI. This is a young project; there is no long-term
support branch yet.

## Reporting a vulnerability

Please report privately rather than opening a public issue:

- GitHub's [private vulnerability reporting](https://github.com/Aakarsh751/robstattm-py/security/advisories/new), or
- email <aakarshg@uw.edu>

Please include what you did, what happened, and what you expected. I will
acknowledge within a week and keep you updated.

## What this package does that is worth reviewing

RobStatTM-Py is a statistics library, but two things about it are worth a
security reviewer's attention.

### It downloads and executes software

`robstattm-py setup` downloads and installs R. Specifically it:

1. Downloads a pinned [micromamba](https://github.com/mamba-org/mamba) release
   from GitHub over HTTPS and **verifies its SHA-256** against a hash committed
   in `src/robstattm_py/_renv/micromamba.py`;
2. Uses it to install R and R packages from
   [conda-forge](https://conda-forge.org/), which are signed and checksummed by
   conda's own infrastructure.

Everything lands in a directory this package owns (`ROBSTATTM_HOME`); no system
location is written to and no elevated privileges are requested.

Relevant properties:

- **Nothing downloads without being asked.** `import robstattm_py` never touches
  the network, never creates directories, and never provisions anything. There
  is a test that enforces this in a subprocess.
- `setup` prints what it will fetch and requires confirmation, or an explicit
  `--yes`. It refuses to assume consent on a non-interactive stdin.
- `--insecure` and `--no-verify-checksum` exist for TLS-intercepting corporate
  networks. They weaken these guarantees and say so.

Note that conda packages may run install scripts, which is inherent to
installing software this way. If that is unacceptable in your environment,
install R through your own trusted channel, RobStatTM-Py will find it
automatically and `setup` is never required.

### It executes R code

The wrappers pass arguments into an embedded R interpreter. Some paths build R
expressions as strings. **Do not pass untrusted input as formulas, package
names, or file paths**, the same caution that applies to any `eval`-like
interface. This library is intended for analysing your own data, not as a
service boundary.

## Out of scope

Vulnerabilities in R itself, in rpy2, in conda-forge packages, or in RobStatTM
should be reported to those projects. I am happy to help route a report if you
are unsure where it belongs.
