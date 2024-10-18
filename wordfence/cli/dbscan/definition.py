from wordfence.wordpress.database import DEFAULT_HOST, DEFAULT_PORT, \
    DEFAULT_USER, DEFAULT_PREFIX, DEFAULT_COLLATION

from ..subcommands import SubcommandDefinition, UsageExample
from ..config.typing import ConfigDefinitions

from .reporting import DATABASE_SCAN_REPORT_CONFIG_OPTIONS

config_definitions: ConfigDefinitions = {
    "host": {
        "short_name": "H",
        "description": "The database hostname",
        "context": "CLI",
        "argument_type": "OPTION",
        "default": DEFAULT_HOST,
        "category": "Database Connectivity"
    },
    "port": {
        "short_name": "P",
        "description": "The database port",
        "context": "CLI",
        "argument_type": "OPTION",
        "default": DEFAULT_PORT,
        "meta": {
            "value_type": int
        },
        "category": "Database Connectivity"
    },
    "user": {
        "short_name": "u",
        "description": "The database user",
        "context": "CLI",
        "argument_type": "OPTION",
        "default": DEFAULT_USER,
        "category": "Database Connectivity"
    },
    "password": {
        "description": "The database password (this option is insecure)",
        "context": "CLI",
        "argument_type": "OPTION",
        "default": None,
        "category": "Database Connectivity"
    },
    "prompt-for-password": {
        "short_name": "p",
        "description": "Prompt for a database password",
        "context": "CLI",
        "argument_type": "FLAG",
        "default": False,
        "category": "Database Connectivity"
    },
    "password-env": {
        "description": "The environment variable name to check for a password",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": "WFCLI_DB_PASSWORD",
        "category": "Database Connectivity"
    },
    "prefix": {
        "short_name": "x",
        "description": "The WordPress database prefix",
        "context": "CLI",
        "argument_type": "OPTION",
        "default": DEFAULT_PREFIX,
        "category": "Database Connectivity"
    },
    "database-name": {
        "short_name": "D",
        "description": "The MySQL database name",
        "context": "CLI",
        "argument_type": "OPTION",
        "default": None,
        "category": "Database Connectivity"
    },
    "collation": {
        "short_name": "C",
        "description": "The collation to use when connecting to MySQL",
        "context": "CLI",
        "argument_type": "OPTION",
        "default": DEFAULT_COLLATION
    },
    "read-stdin": {
        "description": "Read paths from stdin. If not specified, paths will "
                       "automatically be read from stdin when input is not "
                       "from a TTY.",
        "context": "ALL",
        "argument_type": "OPTIONAL_FLAG",
        "default": None
    },
    "path-separator": {
        "short_name": "s",
        "description": "Separator used to delimit paths when reading from "
                       "stdin. Defaults to the null byte.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": "AA==",
        "default_type": "base64"
    },
    **DATABASE_SCAN_REPORT_CONFIG_OPTIONS,
    "require-database": {
        "description": "When enabled, invoking the db-scan command without "
                       "specifying at least one database will trigger an "
                       "error. This is the default behavior when running in "
                       "a terminal.",
        "context": "CLI",
        "argument_type": "OPTIONAL_FLAG",
        "default": None
    },
    "locate-sites": {
        "short_name": "S",
        "description": (
                "Automatically locate WordPress config files to extract "
                "database connection details"
            ),
        "context": "CLI",
        "argument_type": "FLAG",
        "default": None,
        "category": "Site Location"
    },
    "allow-nested": {
        "description": "Allow WordPress installations nested below other "
                       "installations to be identified as targets for "
                       "database scanning",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": True,
        "category": "Site Location"
    },
    "allow-io-errors": {
        "description": "Allow scanning to continue even if an IO error occurs "
                       "while locating WordPress sites. Sites that cannot "
                       "be identified due to IO errors will be excluded from "
                       "scanning. This is the default behavior.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": True,
        "category": "Site Location"
    },
    "use-remote-rules": {
        "description": "If enabled, scanning rules will be pulled from "
                       "the Wordfence API. This is the default behavior.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": True
    },
    "rules-file": {
        "short_name": "R",
        "description": "Path to a JSON file containing scanning rules",
        "context": "ALL",
        "argument_type": "OPTION_REPEATABLE",
        "meta": {
            "accepts_file": True
        }
    },
    "exclude-rules": {
        "short_name": "e",
        "description": "Specify rule IDs to ignore when scanning. May be "
                       "comma-delimited and/or repeated.",
        "context": "ALL",
        "argument_type": "OPTION_REPEATABLE",
        "default": None,
        "meta": {
            "separator": ",",
            "value_type": int
        }
    },
    "include-rules": {
        "short_name": "i",
        "description": "Specify rule IDs to include when scanning. May be "
                       "comma-delimited and/or repeated.",
        "context": "ALL",
        "argument_type": "OPTION_REPEATABLE",
        "default": None,
        "meta": {
            "separator": ",",
            "value_type": int
        }
    }
}

examples = [
    UsageExample(
        'Scan the WordPress database at db.example.com',
        'wordfence db-scan -h db.example.com -p wordpress'
    )
]

definition = SubcommandDefinition(
    name='db-scan',
    usage=[
        '[OPTIONS] [DATABASE_CONFIG_PATH]...',
        '[OPTIONS] -S [WORDPRESS_INSTALLATION_PATH]...'
    ],
    description='Scan for malicious content in WordPress databases',
    config_definitions=config_definitions,
    config_section='DB_SCAN',
    cacheable_types={
            'wordfence.intel.database_rules.DatabaseRuleSet',
            'wordfence.intel.database_rules.DatabaseRule'
        },
    examples=examples,
    accepts_directories=True
)
