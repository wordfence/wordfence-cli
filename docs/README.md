# Wordfence CLI Documentation

Wordfence CLI is a high performance, multi-process, command-line malware scanner written in Python. 

## Contents

- [Installation](Installation.md)
	- [Binaries](Installation.md#binaries)
	- [Wheel Archive](Installation.md#pip-installation-of-the-wheel-archive-file)
	- [Docker](Installation.md#docker)
	- [Manual installation](Installation.md#manual-installation)
- [Configuration](Configuration.md)
- [Output](Output.md)
- **Malware Scanning**
	- [Subcommand Configuration](malware-scan/Configuration.md)
	- [Examples](malware-scan/Examples.md)
		- [Scanning a directory for malware](malware-scan/Examples.md#scanning-a-directory-for-malware)
		- [Running Wordfence CLI in a cron](malware-scan/Examples.md#running-wordfence-cli-in-a-cron)
		- [Piping files from `find` to Wordfence CLI](malware-scan/Examples.md#piping-files-from-find-to-wordfence-cli)
- **Vulnerability Scanning**
	- [Subcommand Configuration](vuln-scan/Configuration.md)
	- [Examples](vuln-scan/Examples.md)
		- [Scanning a single WordPress installation for vulnerabilities](vuln-scan/Examples.md#scanning-a-single-wordpress-installation-for-vulnerabilities)
		- [Running the vulnerability scan in a cron](vuln-scan/Examples.md#running-the-vulnerability-scan-in-a-cron)
- [Frequently Asked Questions](FAQs.md)
