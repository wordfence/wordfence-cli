from ..subcommands import SubcommandDefinition
from ..config.typing import ConfigDefinitions

config_definitions: ConfigDefinitions = {
    }

definition = SubcommandDefinition(
    name='vuln-scan',
    description='Scan WordPress installations for vulnerable software',
    config_definitions=config_definitions,
    config_section='VULN_SCAN'
)
