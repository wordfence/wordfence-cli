from ..subcommands import SubcommandDefinition, UsageExample
from ..config.typing import ConfigDefinitions

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
    "require-path": {
        "description": "When enabled, invoking the count command without "
                       "specifying at least one path will trigger an error. "
                       "This is the default behavior when running in a "
                       "terminal.",
        "context": "CLI",
        "argument_type": "OPTIONAL_FLAG",
        "default": None
    },
    "allow-nested": {
        "description": "When enabled (the default), WordPress installations "
                       "nested below other installations will be included in "
                       "the count.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": True
    },
    "allow-io-errors": {
        "description": "Allow counting to continue if IO errors are "
                       "encountered. Sites that cannot be identified due to "
                       "IO errors will be omitted from the count. This is the "
                       "default behavior.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": True
    }
}

examples = [
    UsageExample(
        'Count the number of WordPress installations under /var/www/',
        'wordfence count-sites /var/www/'
    )
]

definition = SubcommandDefinition(
    name='count-sites',
    usage='[OPTIONS] [PATH]...',
    description='Count the total number of WordPress installations under '
                'the specified path(s)',
    config_definitions=config_definitions,
    config_section='COUNT_SITES',
    cacheable_types=set(),
    examples=examples,
    accepts_directories=True
)
