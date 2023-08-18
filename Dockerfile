FROM python:3.11.4-slim as base

FROM base as build
WORKDIR /app

# copy source code, build wheel, set up venv, and install
COPY wordfence wordfence
COPY pyproject.toml pyproject.toml
RUN pip install build~=0.10
RUN python -m build --wheel
RUN python -m venv /venv
RUN /venv/bin/pip install dist/wordfence-*.whl

FROM base
WORKDIR /venv

# copy venv from build stage
COPY --from=build /venv .
ENV PATH="/venv/bin:${PATH}"
# run the application, bringing in command line arguments
ENTRYPOINT [ "wordfence" ]
