from argparse import ArgumentParser
from types import SimpleNamespace
from typing import Any, List, Dict, Optional

from .cli_parser import CliCanonicalValueExtractor, get_cli_values
from .config_items import ConfigItemDefinition, \
    CanonicalValueExtractorInterface, not_set_token
from .ini_parser import load_ini, get_ini_value_extractor, \
        get_default_ini_value_extractor
from ..subcommands import SubcommandDefinition
from .base_config_definitions import config_map as base_config_map


class Config(SimpleNamespace):

    def __init__(
                self,
                definitions,
                parser: ArgumentParser,
                subcommand: Optional[str],
                ini_path: Optional[str] = None
            ):
        super().__init__()
        self._definitions = definitions
        self._parser = parser
        self.subcommand = subcommand
        self.ini_path = ini_path
        self.trailing_arguments = None

    def values(self) -> Dict[str, Any]:
        result: Dict[str, Any] = dict()
        for prop, value in vars(self).items():
            if (prop.startswith('_') or callable(value) or
                    isinstance(value, classmethod)):
                continue
            result[prop] = value
        return result

    def get(self, property_name, default=None) -> Any:
        return getattr(self, property_name, default)

    def define(self, property_name) -> ConfigItemDefinition:
        return self._definitions[property_name]

    def has_ini_file(self) -> bool:
        return self.ini_path is not None

    def display_help(self) -> None:
        self._parser.print_help()


value_extractors: List = []


def create_config_object(
            subcommand: str,
            definitions: Dict[str, ConfigItemDefinition],
            trailing_arguments: List[str],
            parser,
            *ordered_sources
        ):
    if len(ordered_sources) < 1:
        raise ValueError("At least one configuration source must be passed in")
    target = Config(definitions, parser, subcommand)
    for source in ordered_sources:
        source_extractors: List[CanonicalValueExtractorInterface] = []
        for extractor in value_extractors:
            if extractor.is_valid_source(source):
                source_extractors.append(extractor)
        if len(source_extractors) == 0:
            raise Exception(
                    'No compatible extractor found for provided config source'
                )
        # extract all values from the source and
        # conditionally update the config
        for item_definition in definitions.values():
            new_value = not_set_token
            for extractor in source_extractors:
                new_value = extractor.get_canonical_value(
                        item_definition,
                        source
                    )
                if new_value is not not_set_token:
                    break

            # later values always replace previous values
            if new_value is not not_set_token:
                setattr(target, item_definition.property_name, new_value)
            elif not hasattr(target, item_definition.property_name):
                default = item_definition.default
                if item_definition.has_separator() and \
                        isinstance(default, str):
                    default = default.split(item_definition.meta.separator)
                setattr(target, item_definition.property_name,
                        default)
    target.trailing_arguments = trailing_arguments
    return target


def load_config(subcommand_definitions: Dict[str, SubcommandDefinition]):
    cli_values, trailing_arguments, parser = get_cli_values(
            subcommand_definitions
        )

    if cli_values.subcommand:
        assert cli_values.subcommand in subcommand_definitions
        subcommand_definition = subcommand_definitions[cli_values.subcommand]
        config_map = {
                **base_config_map,
                **subcommand_definition.get_config_map()
            }
    else:
        subcommand_definition = None
        config_map = base_config_map

    ini_values, ini_path = load_ini(cli_values, subcommand_definition)

    if subcommand_definition is not None:
        value_extractors.append(get_ini_value_extractor(subcommand_definition))
    value_extractors.append(get_default_ini_value_extractor())
    value_extractors.append(CliCanonicalValueExtractor())

    instance = create_config_object(
            cli_values.subcommand,
            config_map,
            trailing_arguments,
            parser,
            ini_values,
            cli_values
        )
    instance.ini_path = ini_path
    return instance
