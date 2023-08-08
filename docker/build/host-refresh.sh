#!/bin/bash

if [ -z ${1:+x} ]; then
    echo "You must provide the path to the project (if called from within the root project dir, pass in '.')"
    exit 1
fi

if [ ! -d "$1" ]; then
    echo "The first argument must point to the project directory"
fi

PROJECT_DIR=$(realpath "$1")

docker rmi -f wfcli-build wfcli-build-arm64 2>/dev/null
docker build -t wfcli-build -f "$PROJECT_DIR/docker/build/Dockerfile" "$PROJECT_DIR"
docker build -t wfcli-build-arm64 --platform linux/arm64 -f "$PROJECT_DIR/docker/build/Dockerfile" "$PROJECT_DIR"
docker rm -f wfcli-build-container 2>/dev/null
