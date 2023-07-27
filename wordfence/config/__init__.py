from argparse import Namespace
from configparser import ConfigParser

from .config_items import definitions, ConfigValue, ConfigItemDefinition, AlwaysInvalidExtractor, \
    CanonicalValueExtractorInterface, not_set_token
from .cli_parser import cli_values
from .cli_parser import CliCanonicalValueExtractor
from .ini_parser import ini_values
from .ini_parser import IniCanonicalValueExtractor
from typing import Any, Type, List, Dict
from wordfence.logging import log


class Config:
    def __new__(cls, *args, **kwargs):
        raise TypeError("The Config class cannot be instantiated.")

    @classmethod
    def values(cls) -> Dict[str, Any]:
        result: Dict[str, Any] = dict()
        for prop, value in vars(Config).items():
            if prop.startswith('_') or callable(value) or isinstance(value, classmethod):
                continue
            result[prop] = value
        return result


value_extractors: List = [
    IniCanonicalValueExtractor,
    CliCanonicalValueExtractor
]


def load_canonical_values(definitions: Dict[str, ConfigItemDefinition], *ordered_sources):
    if len(ordered_sources) < 1:
        raise ValueError("At least one configuration source must be passed in")
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
                setattr(Config, item_definition.property_name, new_value)
            elif not hasattr(Config, item_definition.property_name):
                setattr(Config, item_definition.property_name, item_definition.default)


def validate_config() -> None:
    log.warn("Validation not implemented")


load_canonical_values(definitions, ini_values, cli_values)
validate_config()
