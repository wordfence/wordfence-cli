from types import SimpleNamespace
from typing import Any, Type, List, Dict

from wordfence.logging import log
from .cli_parser import CliCanonicalValueExtractor, cli_values, trailing_arguments
from .config_items import ConfigValue, ConfigItemDefinition, AlwaysInvalidExtractor, \
    CanonicalValueExtractorInterface, not_set_token, valid_subcommands, get_config_map_for_subcommand
from .ini_parser import IniCanonicalValueExtractor
from .ini_parser import ini_values


class Config(SimpleNamespace):

    def __init__(self, definitions, subcommand):
        super().__init__()
        self.__definitions = definitions
        self.subcommand = subcommand

    def values(self) -> Dict[str, Any]:
        result: Dict[str, Any] = dict()
        for prop, value in vars(self).items():
            if prop.startswith('_') or callable(value) or isinstance(value, classmethod):
                continue
            result[prop] = value
        return result

    def get(self, property_name) -> Any:
        return getattr(self, property_name)

    def define(self, property_name) -> ConfigItemDefinition:
        return self.__definitions[property_name]


value_extractors: List = [
    IniCanonicalValueExtractor,
    CliCanonicalValueExtractor
]


def create_config_object(definitions: Dict[str, ConfigItemDefinition], *ordered_sources):
    if len(ordered_sources) < 1:
        raise ValueError("At least one configuration source must be passed in")
    target = Config(definitions, cli_values.subcommand)
    for source in ordered_sources:
        # if an appropriate extractor isn't found, an exception will be thrown
        extractor_class: Type[CanonicalValueExtractorInterface] = AlwaysInvalidExtractor
        for extractor in value_extractors:
            if extractor.is_valid_source(source):
                extractor_class = extractor
                break
        # extract all values from the source and conditionally update the config
        for item_definition in definitions.values():
            new_value = extractor_class.get_canonical_value(item_definition, source)

            # later values always replace previous values
            if new_value is not not_set_token:
                setattr(target, item_definition.property_name, new_value)
            elif not hasattr(target, item_definition.property_name):
                setattr(target, item_definition.property_name, item_definition.default)
    return target


def validate_config() -> None:
    log.warn("Validation not implemented")


__instance = None


def load_config():
    global __instance
    if not __instance:
        __instance = create_config_object(get_config_map_for_subcommand(cli_values.subcommand), ini_values, cli_values)
    return __instance
