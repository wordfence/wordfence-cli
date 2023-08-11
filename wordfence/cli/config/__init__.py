import sys
from argparse import Namespace
from configparser import ConfigParser
from types import SimpleNamespace
from typing import Any, Type, List, Dict, Optional

from .cli_parser import CliCanonicalValueExtractor, get_cli_values, parser
from .config_items import ConfigItemDefinition, \
    AlwaysInvalidExtractor, CanonicalValueExtractorInterface, not_set_token, \
    get_config_map_for_subcommand
from .ini_parser import load_ini, get_ini_value_extractor


class Config(SimpleNamespace):

    def __init__(
                self,
                definitions,
                subcommand,
                ini_path: Optional[str] = None
            ):
        super().__init__()
        self.__definitions = definitions
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

    def get(self, property_name) -> Any:
        return getattr(self, property_name)

    def define(self, property_name) -> ConfigItemDefinition:
        return self.__definitions[property_name]

    def has_ini_file(self) -> bool:
        return self.ini_path is not None


__instance: Optional[Config] = None
__ini_path: Optional[str] = None
__ini_values: Optional[ConfigParser] = None
__cli_values: Optional[Namespace] = None

value_extractors: List = []


def create_config_object(definitions: Dict[str, ConfigItemDefinition],
                         trailing_arguments: List[str], *ordered_sources):
    if len(ordered_sources) < 1:
        raise ValueError("At least one configuration source must be passed in")
    target = Config(definitions, __cli_values.subcommand)
    for source in ordered_sources:
        # if an appropriate extractor isn't found, an exception will be thrown
        extractor_class: Type[
            CanonicalValueExtractorInterface] = AlwaysInvalidExtractor
        for extractor in value_extractors:
            if extractor.is_valid_source(source):
                extractor_class = extractor
                break
        # extract all values from the source and
        # conditionally update the config
        for item_definition in definitions.values():
            new_value = (extractor_class
                         .get_canonical_value(item_definition, source))

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


def load_config():
    global __instance
    global __ini_values
    global __cli_values
    if not __instance:
        __cli_values, trailing_arguments = get_cli_values()
        if not __cli_values.subcommand:
            parser.print_help()
            sys.exit()
        __ini_values, __ini_path = load_ini(__cli_values)

        value_extractors.append(get_ini_value_extractor(__cli_values))
        value_extractors.append(CliCanonicalValueExtractor())

        __instance = create_config_object(
            get_config_map_for_subcommand(__cli_values.subcommand),
            trailing_arguments,
            __ini_values,
            __cli_values)
        __instance.ini_path = __ini_path
    return __instance
