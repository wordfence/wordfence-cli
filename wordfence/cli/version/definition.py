from ..subcommands import SubcommandDefinition
from ..config.typing import ConfigDefinitions

config_definitions: ConfigDefinitions = {}

cacheable_types = set()

definition = SubcommandDefinition(
    name='version',
    usage='',
    description='Display the version of Wordfence CLI',
    config_definitions=config_definitions,
    config_section='DEFAULT',
    cacheable_types=cacheable_types,
    requires_config=False
)
