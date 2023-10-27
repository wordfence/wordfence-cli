FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    python3.8 \
    python3.8-dev \
    python3-pip \
    libffi-dev

COPY ./docker/build/entrypoint.sh /root/entrypoint.sh
COPY ./ /root/wordfence-cli

RUN chmod +x /root/entrypoint.sh

ENTRYPOINT ["/bin/bash"]
CMD ["/root/entrypoint.sh"]
