FROM python:3.11-slim as base

# install OS packages
RUN apt-get update && apt-get install -y \
    libpcre3 \
    && rm -rf /var/lib/apt/lists/*

FROM base as build
WORKDIR /app

# copy source code, build wheel, set up venv, and install
COPY wordfence wordfence
COPY pyproject.toml pyproject.toml
RUN pip install build~=0.10
RUN python -m build --wheel
RUN python -m venv /venv
ENV VIRTUAL_ENV="/venv"
ENV PATH="/venv/bin:${PATH}"
RUN pip install dist/wordfence-*.whl

FROM base as final
WORKDIR /venv

# copy venv from build stage
COPY --from=build /venv .
ENV VIRTUAL_ENV="/venv"
ENV PATH="/venv/bin:${PATH}"
# run the application, bringing in command line arguments
ENTRYPOINT [ "wordfence" ]
