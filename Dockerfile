# A ready-to-use RobStatTM-Py environment: R, RobStatTM and Jupyter included.
#
#     docker build -t robstattm-py .
#     docker run --rm -it robstattm-py robstattm-py doctor
#     docker run --rm -p 8888:8888 robstattm-py \
#         jupyter lab --ip=0.0.0.0 --no-browser --allow-root
#
# Built on micromamba rather than a plain Python base for a specific reason:
# rpy2 has no Linux wheels, so pip would have to compile it against an R that
# does not exist yet. conda-forge provides prebuilt rpy2 *and* R, which removes
# both the compiler and the ordering problem.

FROM mambaorg/micromamba:2.0.5

# conda-forge's r-base needs these for a few packages' shared libraries.
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
USER $MAMBA_USER

COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/environment.yml

# Install everything except our own package: the source is not in the image yet,
# and this layer is the expensive one, so it should not be invalidated by an
# edit to the Python code.
RUN sed '/robstattm-py/d; /--no-deps/d; /^  - pip:/d' /tmp/environment.yml > /tmp/deps.yml \
    && micromamba install -y -n base -f /tmp/deps.yml \
    && micromamba clean --all --yes

ARG MAMBA_DOCKERFILE_ACTIVATE=1

COPY --chown=$MAMBA_USER:$MAMBA_USER . /src
RUN python -m pip install --no-deps --no-cache-dir /src

WORKDIR /work

# Fail the build rather than ship an image that cannot start R.
RUN python -m robstattm_py.cli doctor \
    && python -c "\
import robstattm_py as rpm; \
fit = rpm.lmrobdet_mm('zinc ~ copper', data=rpm.datasets.mineral()); \
assert abs(fit.coefficients[0] - 15.2012174) < 1e-4, fit.coefficients; \
print('image verified:', fit.coefficients)"

LABEL org.opencontainers.image.title="RobStatTM-Py" \
      org.opencontainers.image.description="Robust statistics from Python, with R and RobStatTM included" \
      org.opencontainers.image.source="https://github.com/Aakarsh751/robstattm-py" \
      org.opencontainers.image.licenses="MIT"

CMD ["python"]
