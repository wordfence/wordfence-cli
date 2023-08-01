from typing import Any, Type, List, Dict

from wordfence.logging import log
from .cli_parser import CliCanonicalValueExtractor, cli_values, trailing_arguments
from .config_items import ConfigValue, ConfigItemDefinition, AlwaysInvalidExtractor, \
    CanonicalValueExtractorInterface, not_set_token, valid_subcommands, get_config_map_for_subcommand
from .ini_parser import IniCanonicalValueExtractor
from .ini_parser import ini_values


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


def init_config(definitions: Dict[str, ConfigItemDefinition], *ordered_sources):
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
    validate_config()


def validate_config() -> None:
    log.warn("Validation not implemented")


init_config(get_config_map_for_subcommand(cli_values.subcommand), ini_values, cli_values)

# set config values that require special handling
setattr(Config, 'subcommand', cli_values.subcommand)
setattr(Config, 'trailing_arguments', trailing_arguments)
