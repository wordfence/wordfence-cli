# Installation

## Binaries

This is the simplest method for installing CLI. Binaries for Wordfence CLI can be downloaded on the Releases page of the GitHub repository:

[https://github.com/wordfence/wordfence-cli/releases](https://github.com/wordfence/wordfence-cli/releases)

The binaries are signed using GPG. You can find our public key here:

	https://www.wordfence.com/wp-content/uploads/public.asc
	
To verify a signed binary, download both the gzipped binary and the .asc armor file for the architecture you've chosen.

	wget https://www.wordfence.com/wp-content/uploads/public.asc
	gpg --import public.asc

You can optionally sign the public key with your own private key:

	gpg --lsign-key 00B225C7030F26FF4A3D3481F82623ECE1DB0FBB

To verify the download run the following code (replace the file names with the ones you've downloaded):

	gpg --assert-signer 00B225C7030F26FF4A3D3481F82623ECE1DB0FBB --verify wordfence.tar.gz.asc wordfence.tar.gz

If your version of GPG doesn't include `--assert-signer` you can just run:

	gpg --verify wordfence.tar.gz.asc wordfence.tar.gz

You should see output similar to this:

	gpg: Signature made Fri Aug 18 16:27:11 2023 EDT
	gpg:                using EDDSA key 00B225C7030F26FF4A3D3481F82623ECE1DB0FBB
	gpg:                issuer "opensource@wordfence.com"
	gpg: Good signature from "Wordfence <opensource@wordfence.com>" [ultimate]
	gpg: signer '00B225C7030F26FF4A3D3481F82623ECE1DB0FBB' matched

Extract the binary:

	tar xvzf wordfence.tar.gz

Verify the binary works correctly:

	./wordfence scan --version

## Docker

To install Wordfence CLI using Docker, you can clone the GitHub repo to your local environment:

	git clone git@github.com:wordfence/wordfence-cli.git
	cd ./wordfence-cli
	docker build -t wordfence-cli:latest .

Once the Docker image is built, you can start the docker container with the volumes you wish to scan:

	docker run -v /var/www:/var/www wordfence-cli:latest scan --version

## Manual Installation

To install Wordfence CLI manually, you can clone the GitHub repo to your local environment:

	git clone git@github.com:wordfence/wordfence-cli.git
	cd ./wordfence-cli
	pip install -r requirements.txt
	python setup.py
	python main.py scan --version

If you encounter an error about `libpcre.so` similar to this one:

	OSError: libpcre.so: cannot open shared object file: No such file or directory

You may need to install the `libpcre` library. 

