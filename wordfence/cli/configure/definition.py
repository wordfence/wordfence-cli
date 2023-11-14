from ..subcommands import SubcommandDefinition
from ..config.typing import ConfigDefinitions

config_definitions: ConfigDefinitions = {
    "overwrite": {
        "short_name": "o",
        "description": "Overwrite any existing configuration file without "
                       "prompting",
        "context": "CLI",
        "argument_type": "OPTIONAL_FLAG",
        "default": None
    },
    "request-license": {
        "short_name": "r",
        "description": "Automatically request a free licenses without "
                       "prompting",
        "context": "CLI",
        "argument_type": "OPTIONAL_FLAG",
        "default": None
    },
    "workers": {
        "short_name": "w",
        "description": "Specify the number of worker processes to "
                       "use for malware scanning",
        "context": "CLI",
        "argument_type": "OPTION",
        "default": None,
        "meta": {
            "value_type": int
        }
    },
    "default": {
        "short_name": "D",
        "description": "Automatically accept the default values for any "
                       "options that are not explicitly specified. This will "
                       "also result in a free license being requested when "
                       "terms are accepted.",
        "context": "CLI",
        "argument_type": "FLAG",
        "default": False
    }
}

cacheable_types = set()

definition = SubcommandDefinition(
    name='configure',
    usage='',
    description='Interactively configure Wordfence CLI',
    config_definitions=config_definitions,
    config_section='DEFAULT',
    cacheable_types=cacheable_types,
    requires_config=False
)
