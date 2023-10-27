#!/bin/bash

if [ -z ${1:+x} ]; then
    echo "You must provide the path to the project (if called from within the root project dir, pass in '.')"
    exit 1
elif [ ! -d "$1" ]; then
    echo "The first argument must point to the project directory"
    exit 1
elif [ -z ${2:+x} ]; then
    echo "You must provide the architecture as the second argument"
    exit 1
elif [ "$2" != "amd64" ] && [ "$2" != "arm64" ]; then
    echo "Invalid architecture (must be amd64 or arm64)"
    exit 1
fi

PROJECT_DIR=$(realpath "$1")
ARCHITECTURE="$2"

docker rmi -f "wfcli-build-$ARCHITECTURE" 2>/dev/null
docker build \
    --no-cache \
    -t "wfcli-build-${ARCHITECTURE}" \
    --platform "linux/${ARCHITECTURE}" \
    -f "${PROJECT_DIR}/docker/build/build.Dockerfile" \
    "$PROJECT_DIR"
