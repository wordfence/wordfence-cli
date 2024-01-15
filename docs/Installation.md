# Installation

## Installation with `pip` 

This is the simplest method for installing CLI. 

	pip install wordfence

This should build and install an executable of Wordfence CLI at the following directory when run as the `username` user:

	/home/username/.local/bin/wordfence

If run as root, the executable path should be:

	/usr/local/bin/wordfence

Verify the executable works correctly on your system:

	./wordfence version

You should see output similar to this:

	Wordfence CLI 3.0.1

Once this is done, we recommend [reviewing the configuration](Configuration.md) to go through configuring a license followed by [running your first scan](malware-scan/Examples.md).

## Install the Debian package

This method will work for Debian and Debian-based Linux distros (Ubuntu, Linux Mint, Kali, etc) where you have root access to the system. 

	sudo apt install ./wordfence.deb

For older distros, you can also use the following commands to install CLI.

	sudo dpkg -i wordfence.deb
	sudo apt -f install

Verify the executable works correctly on your system:

	wordfence --version

You should see output similar to this:

	Wordfence CLI 3.0.1

Once this is done, we recommend [reviewing the configuration](Configuration.md) to go through configuring a license followed by [running your first scan](malware-scan/Examples.md).

## Install the RPM package

This method will work for Red Hat Enterprise Linux 9 and compatible distributions (AlmaLinux, Rocky Linux, etc) where you have root access to the system. You must have the CodeReady Linux Builder (CRB) repo enabled before installing.

On RHEL, run:

	subscription-manager repos --enable codeready-builder-for-rhel-9-$(arch)-rpms

On RHEL-compatible distributions, run:

	dnf config-manager --set-enabled crb

You should now be able to install the RPM package:

	sudo dnf install ./wordfence-el9.rpm

Verify the executable works correctly on your system:

	wordfence version

You should see output similar to this:

	Wordfence CLI 3.0.1

Once this is done, we recommend [reviewing the configuration](Configuration.md) to go through configuring a license followed by [running your first scan](malware-scan/Examples.md).

## Binaries

Binaries for Wordfence CLI can be downloaded on the Releases page of the GitHub repository (under Assets of each release) along with source code, and the .whl files:

[https://github.com/wordfence/wordfence-cli/releases](https://github.com/wordfence/wordfence-cli/releases)

The binary files are in the format `wordfence_yyyy.tar.gz` where `yyyy` is the CPU architecture. The following example uses `AMD64` as the architecture. 

We recommend verifying the authenticity of the download prior to extracting the archive. You can do this by following [the steps outlined below](#verifying-the-authenticity-of-a-release-asset) prior to following the rest of these installation steps. 

Extract the binary:

	tar xvzf wordfence_amd64.tar.gz

Verify the binary works correctly on your system:

	./wordfence version

You should see output similar to this:

	Wordfence CLI 3.0.1

Once this is done, we recommend [reviewing the configuration](Configuration.md) to go through configuring a license followed by [running your first scan](malware-scan/Examples.md).

## Docker

To install Wordfence CLI using Docker, you can clone the GitHub repo to your local environment:

	git clone git@github.com:wordfence/wordfence-cli.git
	cd ./wordfence-cli
	docker build -t wordfence-cli:latest .

Once the Docker image is built, you can start the docker container with the volumes you wish to scan:

	docker run -v /var/www:/var/www wordfence-cli:latest version

You should see output similar to this:

	Wordfence CLI 3.0.1

Once this is done, we recommend [reviewing the configuration](Configuration.md) to go through configuring a license followed by [running your first scan](malware-scan/Examples.md).

## Manual Installation

To install Wordfence CLI manually, you can clone the GitHub repo to your local environment:

	git clone git@github.com:wordfence/wordfence-cli.git
	cd ./wordfence-cli
	pip install .
	python main.py version

You can additionally build the wheel archive and generate an executable:
	
	pip install build~=0.10
	python -m build --wheel
	pip install dist/wordfence-*.whl

The executable should be installed to `~/.local/bin/wordfence`.

If you encounter an error about `libpcre.so` similar to this one:

	OSError: libpcre.so: cannot open shared object file: No such file or directory

You may need to install the `libpcre` library. 

## Verifying the Authenticity of a Release Asset

The checksum file for all release assets is sgned using GPG as part of the build process. We recommend verifying the authenticity of the checksum file and then verifying the checksum of the downloaded release asset prior to extracting, installing, or executing any code.

To verify the signature of the checksums file, first download and import our public GPG key:

	wget https://www.wordfence.com/wp-content/uploads/public.asc
	gpg --import public.asc

You can optionally sign our public key with your own private key:

	gpg --lsign-key 00B225C7030F26FF4A3D3481F82623ECE1DB0FBB

Download the `checksums.txt` and `checksums.txt.asc` files from GitHub releases. You can then verify the authenticity of the `checksums.txt` file (replace the filenames with paths to the copies you've downloaded):

	gpg --assert-signer 00B225C7030F26FF4A3D3481F82623ECE1DB0FBB --verify checksums.txt.asc checksums.txt

If your version of GPG doesn't include `--assert-signer` you can just run (you may see a warning using this method):

	gpg --verify checksums.txt.asc checksums.txt

You should see output similar to this:

	gpg: Signature made Fri Aug 18 16:27:11 2023 EDT
	gpg:                using EDDSA key 00B225C7030F26FF4A3D3481F82623ECE1DB0FBB
	gpg:                issuer "opensource@wordfence.com"
	gpg: Good signature from "Wordfence <opensource@wordfence.com>" [ultimate]
	gpg: signer '00B225C7030F26FF4A3D3481F82623ECE1DB0FBB' matched

Now that you've verified the checksums file, you can confirm that the checksum of your download matches. For example, if you downloaded the `wordfence_amd64.tar.gz` (the standalone Linux executable for the `x86_64` architecture) to the same directory as `checksums.txt`, you can verify the checksum matches with:

	sha256sum --ignore-missing -c checksums.txt
