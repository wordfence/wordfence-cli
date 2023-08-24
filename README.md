# Wordfence CLI

Wordfence CLI is a multi-process malware scanner written in Python. It's designed to have low memory overhead while being able to utilize multiple cores for scanning large filesystems for malware. Wordfence CLI uses `libpcre` over Python's existing regex libraries for speed and compatibility with our signature set.

## Installation

We have a number of installation methods to install Wordfence CLI in our [installation documentation](/wordfence/wordfence-cli/blob/main/docs/Installation.md) which we'd recommend reviewing to get you scanning for malware in as few steps as possible. If you'd like to install Wordfence CLI manually, you can clone the GitHub repo to your local environment:

	git clone git@github.com:wordfence/wordfence-cli.git
	cd ./wordfence-cli
	pip install .
	python main.py scan --version

You can additionally build the wheel archive and generate an executable:
	
	pip install build~=0.10
	python -m build --wheel
	pip install dist/wordfence-*.whl

The executable should be installed to `~/.local/bin/wordfence`.

### Requirements

- Python >= 3.8
- The C library `libpcre` >= 8.38
- Python packages:
	- `packaging` >= 23.1
	- `requests` >= 2.3

### Obtaining a license

Visit [https://www.wordfence.com/products/wordfence-cli/](https://www.wordfence.com/products/wordfence-cli/) to obtain a license to download our signature set.

## Usage

You can run `wordfence scan --help` for a full list of options that can be passed to Wordfence CLI. Read more about the [configuration options](/wordfence/wordfence-cli/blob/main/docs/Configuration.md) that can be passed to Wordfence CLI.

#### Example

Recursively scanning the `/var/www` directory and writing the results to `/home/username/wordfence-cli.csv`:

	wordfence scan --output-path /home/username/wordfence-cli.csv /var/www

A [full list of examples](/wordfence/wordfence-cli/blob/main/docs/Examples.md) is included in our documentation.

## Documentation

The full documentation for Wordfence CLI can be found [here](/wordfence/wordfence-cli/blob/main/docs/) which includes installation instructions, configuration options, detailed examples, and frequently asked questions.

## License

Wordfence CLI is open source, licensed under GPLv3. The license can be found [here](/wordfence/wordfence-cli/blob/main/LICENSE).
