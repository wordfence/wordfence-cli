# Configuration

Configuration can be set through command line arguments, or configured globally through the wordfence-cli.ini file. Once Wordfence CLI is installed, we recommend running `./wordfence scan --configure` to interactively setup Wordfence CLI's global configuration.

## wordfence-cli.ini

By default, `wordfence-cli.ini` will reside in `~/.config/wordfence/wordfence-cli.ini`. The INI file is best suited for global configuration options for Wordfence CLI. The license is typically all that's needed to be stored in the INI.

## Command line arguments

- `--read-stdin`: Read paths from stdin. If not specified, paths will automatically be read from stdin when input is not from a TTY. Specify `--no-read-stdin` to disable.
- `-s`, `--file-list-separator`: Separator used when listing files via stdin. Defaults to the null byte.
- `--output`: Write results to stdout. This is the default behavior when `--output-path` is not specified. Use `--no-output` to disable.
- `--output-path`: Path to which to write results.
- `--output-columns`: An ordered, comma-delimited list of columns to include in the output. Available columns: `filename`, `signature_id`, `signature_name`, `signature_description`, `matched_text`.
- `-m`, `--output-format`: Output format used for result data.
- `--output-headers`: Whether or not to include column headers in output.
- `-e`, `--exclude-signatures`: Specify rule IDs to exclude from the scan. Can be comma-delimited and/or specified multiple times.
- `-i`, `--include-signatures`: Specify rule IDs to include in the scan. Can be comma-delimited and/or specified multiple times.
- `--images`: Include image files in the scan.
- `-n`, `--include-files`: Only scan filenames that are exact matches. Can be used multiple times.
- `-x`, `--exclude-files`: Do not scan filenames that are exact matches. Can be used multiple times. Denials take precedence over allows.
- `-N`, `--include-files-pattern`: PCRE regex allow pattern. Only matching filenames will be scanned.
- `-X`, `--exclude-files-pattern`: PCRE regex deny pattern. Matching filenames will not be scanned.
- `-z`, `--chunk-size`: Size of file chunks that will be scanned. Use a whole number followed by one of the following suffixes: b (byte), k (kibibyte), m (mebibyte). Defaults to 3m.
- `-M`, `--scanned-content-limit`: The maximum amount of data to scan in each file. Content beyond this limit will not be scanned. Defaults to 50 mebibytes. Use a whole number followed by one of the following suffixes: b (byte), k (kibibyte), m (mebibyte).
- `--match-all`: If set, all possible signatures will be checked against each scanned file. Otherwise, only the first matching signature will be reported.
- `--pcre-backtrack-limit`: The regex backtracking limit for signature evaluation.
- `--pcre-recursion-limit`: The regex recursion limit for signature evaluation.
- `-w`, `--workers`: Number of worker processes used to perform scanning. Defaults to 1 worker process.
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
- `--configure`: Interactively configure Wordfence CLI.
- `--version`: Display the version of Wordfence CLI.
- `--check-for-update`: Whether or not to run the update check.
