FROM ubuntu:22.04

RUN apt update && apt-get install -y debsigs \
    dpkg-sig \
    python3 \
    dh-python \
    python3-setuptools \
    python3-stdeb \
    python3-pip \
    python3-all-dev

COPY ./docker/build/entrypoint.sh /opt/entrypoint.sh
COPY ./ /opt/wordfence-cli

RUN chmod +x /opt/entrypoint.sh

ENTRYPOINT ["/opt/entrypoint.sh"]