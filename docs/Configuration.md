# Configuration

Configuration can be set through command line arguments, or configured globally through the `wordfence-cli.ini` file. Once Wordfence CLI is installed, we recommend running `wordfence configure` to interactively configure Wordfence CLI's global options.

## `wordfence configure` Command Line Arguments

- `-o`, `--overwrite`: Overwrite any existing configuration file without prompting
- `-r`, `--request-license`: Automatically request a free license without prompting
- `-w`, `--workers`: Specify the number of worker processes to use for malware scanning
- `-D`, `--default`: Automatically accept the default values for any options that are not explicitly specified. This will also result in a free license being requested when terms are accepted.

## Global Command Line Arguments

These arguments apply to all subcommands.

**General Options:**

- `-c`, `--configuration`: Path to a configuration INI file to use. (default: `~/.config/wordfence/wordfence-cli.ini`)
- `-l`, `--license`: Specify the license to use.
- `--version`: Display the version of Wordfence CLI.
- `-h`, `--help`: Display help information.
- `--accept-terms`: Automatically accept the terms required to invoke the specified command. The latest terms can be viewed using the `wordfence terms` command  and found at [https://www.wordfence.com/wordfence-cli-license-terms-and-conditions/](https://www.wordfence.com/wordfence-cli-license-terms-and-conditions/ "Wordfence CLI License Terms and Conditions - Wordfence"). Register to receive updated Wordfence CLI Terms of Service via email at [https://www.wordfence.com/products/wordfence-cli/#terms](https://www.wordfence.com/products/wordfence-cli/#terms "Wordfence CLI - Wordfence"). Join our WordPress Security mailing list at [https://www.wordfence.com/subscribe-to-the-wordfence-email-list/](https://www.wordfence.com/subscribe-to-the-wordfence-email-list/ "Get WordPress Security Alerts and Product Updates - Wordfence") to get security alerts, news, and research directly to your inbox.

**Output Control:**

- `--banner`: Display the Wordfence banner in command output when running in a TTY/terminal. (use `--no-banner` to disable)
- `--color`: Enable ANSI escape sequences in output.

**Email:**

- `-E`, `--email`: Email address(es) to which to send reports.
	* `--email-from`: The From address to use when sending emails. If not specified, the current username and hostname will be used.
	* `--smtp-host`: The host name of the SMTP server to use for sending email.
	* `--smtp-port`: The port of the SMTP server to use for sending email.
	* `--smtp-tls-mode`: The SSL/TLS mode to use when communicating with the SMTP server. none disables TLS entirely. smtps requires TLS for all communication while starttls will negotiate TLS if supported using the STARTTLS SMTP command. Options: `none`, `smtps`, `starttls` (default: `starttls`)
	* `--smtp-user`: The username for authenticating with the SMTP server.
	* `--smtp-password`: The password for authentication with the SMTP server. This should generally be specified in an INI file as including passwords as command line arguments can expose them to other users on the same system.
	* `--sendmail-path`: The path to the sendmail executable. This will be used to send email if SMTP is not configured. (default: `sendmail`)

**Logging:**

- `-v`, `--verbose`: Enable verbose logging. If not specified, verbose logging will be enabled automatically if stdout is a TTY. (use `--no-verbose` to disable)
- `-d`, `--debug`: Enable debug logging. (use `--no-debug` to disable)
- `-q`, `--quiet`: Suppress all output other than scan results. (use `--no-quiet` to disable)
	* `--prefix-log-levels`: Prefix log messages with their respective levels. This is enabled by default when colored output is not enabled.
- `-L`, `--log-level`: Only log messages at or above the specified level. Options: `DEBUG`, `VERBOSE`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

**Caching:**

- `--cache-directory`: A path to use for cache files. (default: `~/.cache/wordfence`)
- `--cache`: Enable caching. Caching is enabled by default. (use `--no-cache` to disable)
- `--purge-cache`: Purge any existing values from the cache.

## wordfence-cli.ini

By default, the configuration file will reside at `~/.config/wordfence/wordfence-cli.ini`. This INI file is best suited for global configuration options for Wordfence CLI. The license is the only item that's typically configured here.

### Global INI Options

```ini
[DEFAULT]
license = <your license key>
verbose = [on|off]
debug = [on|off]
banner = [on|off]
quiet = [on|off]
email = <recipient email address for reports>
email_from = <sender email address for reports>
smtp_host = <hostname of SMTP server for mailing reports>
smtp_port = <port for SMTP server for mailing reports>
smtp_tls_mode = [none|smtps|starttls]
smtp_user = <username>
smtp_password = [on|off]
sendmail_path = <path to sendmail executable, used when SMTP is not configured>
cache_directory = <path to a directory to use for caching>
cache = [on|off]
```

### Subcommand INI Options

See documentation for each [subcommand](Subcommands.md) for its respective INI options. Most command line options can also be set in the INI file. Generally, only settings that should be applied every time CLI is invoked should be stored in the config file. For example, don't store options specific to one site being scanned in the global config file. Global options may also be overwritten for each subcommand section.
