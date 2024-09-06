from wordfence.wordpress.database import DEFAULT_HOST, DEFAULT_PORT, \
    DEFAULT_USER, DEFAULT_PREFIX

from ..subcommands import SubcommandDefinition, UsageExample
from ..config.typing import ConfigDefinitions

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
    usage='[OPTIONS] [DATABASE_NAME]...',
    description='Scan for malicious content in a WordPress databases',
    config_definitions=config_definitions,
    config_section='DB_SCAN',
    cacheable_types=set(),
    examples=examples
)
