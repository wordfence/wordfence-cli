import importlib
from types import ModuleType
from typing import Optional, Dict

from .config.typing import ConfigDefinitions
from .config.config_items import config_definitions_to_config_map, \
        ConfigItemDefinition

VALID_SUBCOMMANDS = {
        'scan',
        'vuln-scan'
    }


def map_subcommand_to_module_name(subcommand: str) -> str:
    return subcommand.replace('-', '')


def import_subcommand_module(
            subcommand: str,
            submodule: Optional[str] = None
        ) -> ModuleType:
    name = map_subcommand_to_module_name(subcommand)
    if submodule is None:
        submodule = name
    target = f'.{name}.{submodule}'
    return importlib.import_module(
            target,
            package='wordfence.cli'
        )


class SubcommandDefinition:

    def __init__(
                self,
                name: str,
                description: str,
                config_definitions: ConfigDefinitions,
                config_section: str
            ):
        self.name = name
        self.description = description
        self.config_definitions = config_definitions
        self.config_section = config_section
        self.config_map = None

    def get_config_map(self) -> Dict[str, ConfigItemDefinition]:
        if self.config_map is None:
            self.config_map = config_definitions_to_config_map(
                    self.config_definitions
                )
        return self.config_map


def load_subcommand_definition(subcommand: str) -> SubcommandDefinition:
    module = import_subcommand_module(subcommand, 'definition')
    assert hasattr(module, 'definition')
    assert isinstance(module.definition, SubcommandDefinition)
    return module.definition


def load_subcommand_definitions() -> Dict[str, SubcommandDefinition]:
    definitions = dict()
    for subcommand in VALID_SUBCOMMANDS:
        definitions[subcommand] = load_subcommand_definition(subcommand)
    return definitions
