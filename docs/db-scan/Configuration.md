# Database Scan Configuration

Configuration can be set through command line arguments or configured globally in `wordfence-cli.ini`. After installing Wordfence CLI, run `./wordfence configure` to interactively create the global configuration file.

## wordfence-cli.ini

The default configuration path is `~/.config/wordfence/wordfence-cli.ini`. Global options such as the license key or cache directory should live in the `[DEFAULT]` section, while database scan specific settings belong in `[DB_SCAN]`.

	[DEFAULT]
	license = xxx
	cache-directory = /usr/local/wordfence-cli

	[DB_SCAN]
	host = db.example.com
	user = wordpress
	database-name = wordpress
	prompt-for-password = true
	output-format = human

## Database Scan Command Line Arguments

- `-H`, `--host`: Database hostname. Defaults to `localhost`.
- `-P`, `--port`: Database port. Defaults to `3306`.
- `-u`, `--user`: Database user. Defaults to `root`.
- `--password`: Provide the database password via the command line. This is insecure and should be avoided in favor of prompting or environment variables.
- `-p`, `--prompt-for-password`: Prompt for the database password on invocation.
- `--password-env`: Environment variable containing the database password. Defaults to `WFCLI_DB_PASSWORD`.
- `-x`, `--prefix`: WordPress database prefix. Defaults to `wp_`.
- `-D`, `--database-name`: Name of the database to scan.
- `-C`, `--collation`: Collation to use when connecting to MySQL. Defaults to `utf8mb4_unicode_ci`.
- `--read-stdin`: Force reading database configuration paths from stdin. When stdin is not a terminal, the command automatically reads paths without specifying this flag.
- `-s`, `--path-separator`: Separator used when reading paths from stdin. Defaults to the null byte (`AA==` in base64 form).
- `--require-database`: Error if no databases are provided. This is automatically enforced when running interactively.
- `-S`, `--locate-sites`: Scan one or more filesystem paths for `wp-config.php` files and extract database credentials automatically.
- `--allow-nested`: Permit nested WordPress installations when locating sites. Enabled by default.
- `--allow-io-errors`: Continue locating sites when IO errors occur. Enabled by default.
- `--use-remote-rules`: Pull the latest database scanning rules from the Wordfence API. Enabled by default.
- `-R`, `--rules-file`: Path to a JSON rules file to merge into the database rule set. May be provided multiple times.
- `-e`, `--exclude-rules`: Rule IDs to ignore when scanning. Accepts comma-delimited lists and repeated flags.
- `-i`, `--include-rules`: Rule IDs to include when scanning. Accepts comma-delimited lists and repeated flags.
- `--output`: Write results to stdout (default when `--output-path` is not set).
- `--output-path`: Destination file for scan results.
- `--output-columns`: Comma-delimited list of columns to include in the output. Available columns: `table`, `rule_id`, `rule_description`, `row`. Column customization is supported for `csv`, `tsv`, `null-delimited`, and `line-delimited` formats.
- `-m`, `--output-format`: Output format for results. Supported values: `human` (default), `csv`, `tsv`, `null-delimited`, `line-delimited`.
- `--output-headers`: Include column headers in formats that support them (`csv`, `tsv`, `null-delimited`, `line-delimited`).

When `--locate-sites` is not used, each trailing argument should be a JSON file containing a list of database configurations in the following shape:

	[
	  {
	    "name": "wordpress",
	    "user": "wordpress",
	    "password": "example",
	    "host": "db.example.com",
	    "port": 3306,
	    "collation": "utf8mb4_unicode_ci",
	    "prefix": "wp_"
	  }
	]

Entries may omit `port`, `collation`, or `prefix`; defaults are applied automatically.

When databases are discovered through `--locate-sites` or provided via JSON files, connection details from those sources override the command-line defaults for each database.
