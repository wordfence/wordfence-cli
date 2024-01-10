from ..subcommands import SubcommandDefinition
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
        "description": "When enabled, invoking the remediate command without "
                       "specifying at least one path will trigger an error. "
                       "This is the default behavior when running in a "
                       "terminal.",
        "context": "CLI",
        "argument_type": "OPTIONAL_FLAG",
        "default": None
    },
}

definition = SubcommandDefinition(
    name='count-sites',
    usage='[OPTIONS] [PATH]...',
    description='Count the total number of WordPress installations under '
                'the specified path(s)',
    config_definitions=config_definitions,
    config_section='COUNT_SITES',
    cacheable_types=set(),
)
