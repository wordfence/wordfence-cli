from ..subcommands import SubcommandDefinition
from ..config.typing import ConfigDefinitions

config_definitions: ConfigDefinitions = {}

cacheable_types = set()

definition = SubcommandDefinition(
    name='configure',
    usage='',
    description='Interactively configure FW Scanner',
    config_definitions=config_definitions,
    config_section='DEFAULT',
    cacheable_types=cacheable_types,
    requires_config=False
)
