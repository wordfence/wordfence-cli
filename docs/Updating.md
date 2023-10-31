# Updating your Installation

## Updating with `pip` 

Use the following to update to the latest release of Wordfence CLI:

	pip install --upgrade wordfence

## Binaries

The releases page in GitHub will have the most recently available binaries for download:

[https://github.com/wordfence/wordfence-cli/releases](https://github.com/wordfence/wordfence-cli/releases)

The binary files are in the format `wordfence_yyyy.tar.gz` where `yyyy` is the CPU architecture. The following example uses `AMD64` as the architecture. 

We recommend verifying the authenticity of the download prior to extracting the archive. You can do this by following [the steps outlined in the installation document](Installation.md#verifying-the-authenticity-of-a-release-asset) prior to following the rest of these updating steps. 

Extract the binary:

	tar xvzf wordfence_amd64.tar.gz

Verify the binary works correctly on your system:

	./wordfence --version

You should see output similar to this:

	Wordfence CLI 2.0.1

Copy the binary to the path you've installed your existing Wordfence CLI binary.

## Docker

If you've followed our [installation instructions for Docker](Installation.md#docker), you can `cd` into the source code directory and run `git pull` to fetch the latest version. The `main` branch is kept up-to-date with the most recent stable release.

## Manual Installation

Updating a manual/development installation can be done by using `git pull` in the source code directory. The `main` branch is kept up-to-date with the most recent stable release.