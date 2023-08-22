#!/bin/bash

if [ -z ${1:+x} ]; then
    echo "You must provide the path to the project (if called from within the root project dir, pass in '.')"
    exit 1
fi

if [ ! -d "$1" ]; then
    echo "The first argument must point to the project directory"
fi

PROJECT_DIR=$(realpath "$1")
ARCHITECTURES=("amd64" "arm64")

function build_image() {
    ARCHITECTURE="$1"
    docker rmi -f "wfcli-build-$ARCHITECTURE" 2>/dev/null
    docker build \
        -t "wfcli-build-${ARCHITECTURE}" \
        --platform "linux/${ARCHITECTURE}" \
        -f "${PROJECT_DIR}/docker/build/Dockerfile" \
        "$PROJECT_DIR"
}

for arch in "${ARCHITECTURES[@]}"; do
    build_image "$arch"
done
