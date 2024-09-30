FROM almalinux:9.3

RUN dnf -y upgrade && \
    dnf -y install dnf-plugins-core && \
    dnf config-manager --set-enabled crb && \
    dnf -y install epel-release && \
    dnf -y install rpmdevtools \
        rpm-build \
        python3.11-devel \
        pyproject-rpm-macros \
        python3.11-pip \
        python3.11-wheel \
        python3.11-pytest \
        python3.11-requests \
        python3-tomli \
        python3-mysqlclient

RUN pip-3.11

COPY ./docker/build/entrypoint.sh /root/entrypoint.sh
COPY ./ /root/wordfence-cli

RUN chmod +x /root/entrypoint.sh

ENTRYPOINT ["/bin/bash"]
CMD ["/root/entrypoint.sh"]
