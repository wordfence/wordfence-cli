#!/bin/bash

if [ -z ${1:+x} ]; then
    echo "You must provide the path to the project (if called from within the root project dir, pass in '.')"
    exit 1
fi

if [ ! -d "$1" ]; then
    echo "The first argument must point to the project directory"
fi

PROJECT_DIR=$(realpath "$1")

echo "output path: $PROJECT_DIR/docker/build/volumes/output"
ARCHITECTURES=("amd64" "arm64")

function build_and_package() {
    ARCHITECTURE="$1"
    GPG_HOME_DIR=$(gpgconf --list-dirs homedir)
    GPG_SOCKET=$(gpgconf --list-dirs agent-socket)
    CONTAINER_GPG_HOME_DIR="/var/run/host_gpg_home_dir"
    docker run \
        -it \
        --rm \
        --name "wfcli-build-container-${ARCHITECTURE}" \
        --platform "linux/${ARCHITECTURE}" \
        -v "${PROJECT_DIR}/docker/build/volumes/output/:/root/output:rw" \
        -v "${PROJECT_DIR}/docker/build/volumes/debian/:/root/debian:rw" \
        -v "${GPG_HOME_DIR}:${CONTAINER_GPG_HOME_DIR}:rw" \
        -v "${GPG_SOCKET}:${CONTAINER_GPG_HOME_DIR}/S.gpg-agent:rw" \
        -e "CONTAINER_GPG_HOME_DIR=${CONTAINER_GPG_HOME_DIR}" \
        "wfcli-build-$ARCHITECTURE"
}

for arch in "${ARCHITECTURES[@]}"
do
    build_and_package "$arch"
done
