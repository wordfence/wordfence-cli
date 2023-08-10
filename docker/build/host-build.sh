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

echo "output path: $PROJECT_DIR/docker/build/volumes/output"
ARCHITECTURES=("amd64" "arm64")

function build_and_package() {
    ARCHITECTURE="$1"
    docker run -it --rm --name "wfcli-build-container-$ARCHITECTURE" --platform "linux/$ARCHITECTURE" -v "$PROJECT_DIR"/docker/build/volumes/output/:/opt/output -v "$PROJECT_DIR"/docker/build/volumes/debian/:/opt/debian -v "$KEYS_DIR":/opt/keys "wfcli-build-$ARCHITECTURE"
}

for arch in "${ARCHITECTURES[@]}"
do
    build_and_package "$arch"
done
