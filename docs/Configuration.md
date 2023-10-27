# Configuration

Configuration can be set through command line arguments, or configured globally through the wordfence-cli.ini file. Once Wordfence CLI is installed, we recommend running `./wordfence configure` to interactively setup Wordfence CLI's global configuration.

## wordfence-cli.ini

By default, `wordfence-cli.ini` will reside in `~/.config/wordfence/wordfence-cli.ini`. The INI file is best suited for global configuration options for Wordfence CLI. The license is typically all that's needed to be stored in the INI.

## Command line arguments

- `-c`, `--configuration`: Path to a configuration INI file to use (defaults to "~/.config/wordfence/wordfence-cli.ini").
- `-l`, `--license`: Specify the license to use.
- `--cache-directory`: A path to use for cache files.
- `--cache`: Whether or not to enable the cache.
- `--purge-cache`: Purge any existing values from the cache.
- `-v`, `--verbose`: Enable verbose logging. If not specified, verbose logging will be enabled automatically if stdout is a TTY. Use `--no-verbose` to disable.
- `-d`, `--debug`: Enable debug logging.
- `-q`, `--quiet`: Suppress all output other than scan results.
- `--banner`: Display the Wordfence banner in command output when running in a TTY/terminal.
- `--progress`: Display scan progress in the terminal with a `curses` interface.
- `--version`: Display the version of Wordfence CLI.
- `--check-for-update`: Whether or not to run the update check.
