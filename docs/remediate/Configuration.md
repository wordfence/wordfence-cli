# Remediation Configuration

Remediation can be configured using either command line arguments, the [INI file](../Configuration.md), or a combination of both.

## Command Line Arguments

- `--read-stdin`: Read paths from stdin
- `-s`, `--path-separator`: Path separator when reading from stdin, defaults to null byte
- `--require-path`: Require at least one path be provided for scanning
- `--allow-nested`: Allow nested WordPress installations
- `--allow-io-errors`: Allow counting to continue if IO errors are encountered

# INI Options

```ini
[COUNT_SITES]
# Read paths from stdin
read_stdin = [on|off]
# Separator string when reading paths from stdin, defaults to null byte
path_separator = <separator>
allow_nested = [on|off]
allow_io_errors = [on|off]
```
