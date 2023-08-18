FROM python:3.11.4-slim
WORKDIR /usr/src/app

# copy source code and install
COPY wordfence wordfence
COPY pyproject.toml pyproject.toml
RUN pip install . && rm -rf build *.egg-info

# run the application, bringing in command line arguments
ENTRYPOINT [ "wordfence" ]
