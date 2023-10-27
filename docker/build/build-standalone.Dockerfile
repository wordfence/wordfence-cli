FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    python3 \
    python3-all \
    python3-pip

COPY ./docker/build/entrypoint.sh /root/entrypoint.sh
COPY ./ /root/wordfence-cli

RUN chmod +x /root/entrypoint.sh

ENTRYPOINT ["/bin/bash"]
CMD ["/root/entrypoint.sh"]
