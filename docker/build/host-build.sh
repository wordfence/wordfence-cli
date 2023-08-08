#!/bin/bash

if [ -z ${1:+x} ]; then
    echo "You must provide the path to the project (if called from within the root project dir, pass in '.')"
    exit 1
fi

if [ ! -d "$1" ]; then
    echo "The first argument must point to the project directory"
fi

PROJECT_DIR=$(realpath "$1")

if [ -z ${2:+x} ]; then
    echo "You must provide the path to the signing key folder"
    exit 1
fi

if [ ! -d "$2" ]; then
    echo "The second argument must point to a folder containing the signing key as 'signing-key.asc'"
fi

KEYS_DIR=$(realpath "$2")

docker rm -f wfcli-build-container wfcli-build-container-arm64 2>/dev/null
echo "output path: $PROJECT_DIR/docker/build/volumes/output"
docker run -it --name wfcli-build-container -v "$PROJECT_DIR"/docker/build/volumes/output/:/opt/output -v "$KEYS_DIR":/opt/keys wfcli-build
docker run -it --name wfcli-build-container-arm64 --platform linux/arm64 -v "$PROJECT_DIR"/docker/build/volumes/output/:/opt/output -v "$KEYS_DIR":/opt/keys wfcli-build-arm64
