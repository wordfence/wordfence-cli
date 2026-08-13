# Wordfence CLI

> [!WARNING]
> Wordfence CLI is no longer available for new Free or Premium licenses.
> The Free version of WF-CLI will reach end-of-life on September 30th, 2026. After that date, the Free version will no longer be supported.
> Existing Wordfence CLI Premium licenses will remain active and supported until their current license term expires. Premium licenses will not be renewed after expiration, and no new Premium licenses will be issued going forward.
> Current Premium customers may continue to access support, documentation, and applicable downloads through the end of their active license term.

 Wordfence CLI is an open source, high performance, multi-process security scanner, written in Python, that quickly scans network filesystems to detect PHP/other malware and WordPress vulnerabilities. CLI is parallelizable, can be scheduled, can accept input via pipe, and can pipe output to other commands.

## Installation

We have a number of installation methods to install Wordfence CLI in our [installation documentation](docs/Installation.md) which we'd recommend reviewing to get you scanning for malware in as few steps as possible. 

We recommend installing using `pip`:

	pip install wordfence

If you'd like to install Wordfence CLI manually or use CLI for development, you can clone the GitHub repo to your local environment:

	git clone git@github.com:wordfence/wordfence-cli.git
	cd ./wordfence-cli
	pip install .
	python main.py version

### Requirements

- Python >= 3.8
- The C library `libpcre` >= 8.38
- Python packages:
	- `packaging` >= 21.0 
	- `requests` >= 2.3
	- `mysql-connector-python` >= 8.0

## Usage

You can run `wordfence help` for a full list of options that can be passed to Wordfence CLI. Read more about the [configuration options](docs/Configuration.md) that can be passed to Wordfence CLI.

#### Scanning a directory for malware

Recursively scanning the `/var/www` directory for malware:

	wordfence malware-scan /var/www

A [full list of examples for the malware scan](docs/malware-scan/Examples.md) is included in our documentation.

#### Scanning a WordPress installation for vulnerabilities

Scanning the `/var/www/wordpress` directory for vulnerabilities. 

	wordfence vuln-scan /var/www/wordpress

A [full list of examples for the vulnerability scan](docs/vuln-scan/Examples.md) is included in our documentation.

## Documentation

The full documentation for Wordfence CLI can be found [here](docs/) which includes installation instructions, configuration options, detailed examples, and frequently asked questions.

## License

Wordfence CLI is open source, licensed under GPLv3. The license can be found [here](LICENSE).

## Contributing

See [our contribution guidelines](CONTRIBUTING.md).
