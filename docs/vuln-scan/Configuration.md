# Vulnerability Scan Configuration

Configuration can be set through command line arguments, or configured globally through the wordfence-cli.ini file. Once Wordfence CLI is installed, we recommend running `./wordfence --configure` to interactively setup Wordfence CLI's global configuration.

## wordfence-cli.ini

By default, `wordfence-cli.ini` will reside in `~/.config/wordfence/wordfence-cli.ini`. The INI file is best suited for global configuration options for Wordfence CLI. The license is typically all that's needed to be stored in the INI. You can optionally store the arguments that appear below in the INI if you choose. Keep in mind, that the examples in the documentation here may not work as expected when using scan options stored in the INI.

In order to store vulnerability scan specific configuration in the INI file, you should use `[VULN-SCAN]` as the INI section. Here's basic example of an INI file that uses default configuration options along with vulnerability scan options:

	[DEFAULT]
	license = xxx
	cache-directory = /usr/local/wordfence-cli

	[VULN-SCAN]
	feed = scanner
	exclude-vulnerability = 99999

## Vulnerability Scan Command Line Arguments

- `--read-stdin`: Read WordPress base paths from stdin. If not specified, paths will automatically be read from stdin when input is not from a TTY. Specify --no-read-stdin to disable.
- `-s`, `--path-separator`: Separator used to delimit paths when reading from stdin. Defaults to the null byte.
- `-w`, `--wordpress-path`: Path to the root of a WordPress installation to scan for core vulnerabilities.
- `-p`, `--plugin-directory`: Path to a directory containing WordPress plugins to scan for vulnerabilities.
- `-t`, `--theme-directory`: Path to a directory containing WordPress themes to scan for vulnerabilities.
- `--output`: Write results to stdout. This is the default behavior when `--output-path` is not specified. Use `--no-output` to disable.
- `--output-path`: Path to which to write results.
- `--output-columns`: An ordered, comma-delimited list of columns to include in the output. Available columns: `software_type`, `slug`, `version`, `id`, `title`, `link,` `description`, `cve`, `cvss_vector`, `cvss_score`, `cvss_rating`, `cwe_id`, `cwe_name`, `cwe_description`, `patched`, `remediation`, `published`, `updated`
- `-m`, `--output-format`: Output format used for result data.
- `--output-headers`: Whether or not to include column headers in output
- `-e`, `--exclude-vulnerability`: Vulnerability IDs to exclude from scan results.
- `-i`, `--include-vulnerability`: Vulnerabilitiy IDs to include in scan results.
- `-I`, `--informational`: Whether or not to include informational vulnerability records in results.
- `-f`, `--feed`: The feed to use for vulnerability information. The production feed provides additional details that are not included in the scanner feed while the scanner feed includes additional vulnerabilities that do not yet have sufficient information to be included in the production feed.
