from ..subcommands import SubcommandDefinition, UsageExample
from ..config.typing import ConfigDefinitions
from .reporting import REMEDIATION_REPORT_CONFIG_OPTIONS

config_definitions: ConfigDefinitions = {
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
    **REMEDIATION_REPORT_CONFIG_OPTIONS,
    "output-unremediated": {
        "short_name": "u",
        "description": "Only include unremediated paths in the output.",
        "context": "CLI",
        "argument_type": "FLAG",
        "default": False,
        "category": "Output Control"
    },
    "require-path": {
        "description": "When enabled, invoking the remediate command without "
                       "specifying at least one path will trigger an error. "
                       "This is the default behavior when running in a "
                       "terminal.",
        "context": "CLI",
        "argument_type": "OPTIONAL_FLAG",
        "default": None
    },
}

examples = [
    UsageExample(
        'Restore the original contents of a plugin file',
        'wordfence remediate /var/www/html/wp-content/plugins/hello.php'
    ),
    UsageExample(
        'Restore all files in a theme directory and output the results to a '
        'CSV file',
        'wordfence remediate --output-format csv --output-path '
        '/tmp/wfcli-remediation-results.csv --output-headers '
        '/var/www/html/wp-content/themes/twentytwentythree'
    ),
    UsageExample(
        'Automatically detect and remediate malware under /var/www/wordpress',
        'wordfence malware-scan --output-columns filename -m null-delimited '
        '/var/www/wordpress | wordfence remediate'
    )
]

definition = SubcommandDefinition(
    name='remediate',
    usage='[OPTIONS] [PATH]...',
    description='Remediate malware by restoring the content of known files',
    long_description='Known files will be overwritten with their original '
                     'content from the WordPress.org repo. Any intentional '
                     'modifications will be lost if files are remediated. '
                     'Performing a backup of existing files prior to '
                     'remediation is recommended.',
    config_definitions=config_definitions,
    config_section='REMEDIATE',
    cacheable_types=set(),
    examples=examples
)
