# Wordfence CLI Documentation

Wordfence CLI is a high performance, multi-process, command-line malware scanner written in Python. 

## Contents

- [Installation](Installation.md)
	- [Installation with `pip`](Installation.md#installation-with-pip)
	- [Install the Debian package](Installation.md#install-the-debian-package)
	- [Install the RPM package](Installation.md#install-the-rpm-package)
	- [Binaries](Installation.md#binaries)
	- [Docker](Installation.md#docker)
	- [Manual Installation](Installation.md#manual-installation)
- [Updating](Updating.md)
- [Configuration](Configuration.md)
- [Output](Output.md)
- [Configuring your server to send email](Email.md)
- **Malware Scanning**
	- [Subcommand Configuration](malware-scan/Configuration.md)
	- [Automatic Remediation](malware-scan/Remediation.md)
	- [Examples](malware-scan/Examples.md)
		- [Scanning a single directory for malware](malware-scan/Examples.md#scanning-a-single-directory-for-malware)
		- [Writing malware scan results to a CSV](malware-scan/Examples.md#writing-malware-scan-results-to-a-csv)
		- [Running Wordfence CLI in a cron](malware-scan/Examples.md#running-wordfence-cli-in-a-cron)
		- [Piping files from `find` to Wordfence CLI](malware-scan/Examples.md#piping-files-from-find-to-wordfence-cli)
- **Vulnerability Scanning**
	- [Subcommand Configuration](vuln-scan/Configuration.md)
	- [Examples](vuln-scan/Examples.md)
		- [Scanning a single WordPress installation for vulnerabilities](vuln-scan/Examples.md#scanning-a-single-wordpress-installation-for-vulnerabilities)
		- [Writing vulnerability scan results to a CSV](vuln-scan/Examples.md#writing-vulnerability-scan-results-to-a-csv)
		- [Running the vulnerability scan in a cron](vuln-scan/Examples.md#running-the-vulnerability-scan-in-a-cron)
- [Autocomplete of CLI's subcommands and parameters](Autocomplete.md)
- [Frequently Asked Questions](FAQs.md)
