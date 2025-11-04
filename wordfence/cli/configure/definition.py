from ..subcommands import SubcommandDefinition, UsageExample
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
        "description": "Automatically request a free license without "
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

examples = [
    UsageExample(
        'Interactively configure Wordfence CLI',
        'wordfence configure'
    ),
    UsageExample(
        'Non-interactively configure Wordfence CLI to use 4 worker processes '
        'and the default values for all other options, automatically '
        'accepting the terms and requesting a free license',
        'wordfence configure --default --workers 4 --accept-terms'
    )
]

definition = SubcommandDefinition(
    name='configure',
    usage='',
    description='Configure Wordfence CLI',
    config_definitions=config_definitions,
    config_section='DEFAULT',
    cacheable_types=cacheable_types,
    requires_config=False,
    examples=examples
)
