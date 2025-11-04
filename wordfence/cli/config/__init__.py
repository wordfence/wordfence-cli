from __future__ import annotations

import os
from typing import TYPE_CHECKING, List, Dict, Tuple
from dataclasses import dataclass

from .cli_parser import CliCanonicalValueExtractor, get_cli_values
from .config_items import ConfigItemDefinition, \
    CanonicalValueExtractorInterface, not_set_token
from .ini_parser import load_ini, get_ini_value_extractor, \
        get_default_ini_value_extractor
from .base_config_definitions import config_map as base_config_map
from .config import Config

if TYPE_CHECKING:
    from ..helper import Helper
    from ..subcommands import SubcommandDefinition


value_extractors: List = []


class RenamedSubcommandException(Exception):

    def __init__(self, old: str, new: str):  # noqa: B042
        self.old = old
        self.new = new


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
                target.sources[item_definition.property_name] = \
                    extractor.get_context()
                try:
                    target.defaulted_options.remove(
                            item_definition.property_name
                        )
                except KeyError:
                    pass  # Ignore options that weren't previously defaulted
            elif not hasattr(target, item_definition.property_name):
                default = item_definition.default
                if item_definition.has_separator() and \
                        isinstance(default, str):
                    default = default.split(item_definition.meta.separator)
                setattr(target, item_definition.property_name,
                        default)
                target.defaulted_options.add(item_definition.property_name)
    target.trailing_arguments = trailing_arguments
    return target


def _get_renamed_subcommand(
            subcommand: str,
            definitions: Dict[str, 'SubcommandDefinition']
        ) -> str:
    for definition in definitions.values():
        if subcommand in definition.previous_names:
            return definition.name
    raise KeyError(
            f'Subcommand {subcommand} does not appear to have been renamed'
        )


def resolve_config_map(subcommand_definition: 'SubcommandDefinition'):
    return {
            **base_config_map,
            **subcommand_definition.get_config_map()
        }


@dataclass
class GlobalConfig:
    debug: bool = False


def load_config(
            subcommand_definitions: Dict[str, 'SubcommandDefinition'],
            helper: 'Helper',
            subcommand: str = None,
            global_config: GlobalConfig = None
        ) -> Tuple[Config, 'SubcommandDefinition']:
    cli_values, trailing_arguments, parser = get_cli_values(
            subcommand_definitions,
            helper
        )

    if global_config is not None:
        global_config.debug = False if cli_values.debug is not_set_token \
            else cli_values.debug

    if subcommand is None:
        subcommand = cli_values.subcommand

    if subcommand:
        try:
            subcommand_definition = subcommand_definitions[subcommand]
        except KeyError:
            raise RenamedSubcommandException(
                    subcommand,
                    _get_renamed_subcommand(
                        subcommand,
                        subcommand_definitions
                    )
                )
        config_map = resolve_config_map(subcommand_definition)

    else:
        subcommand_definition = None
        config_map = base_config_map

    ini_values, ini_path = load_ini(cli_values, subcommand_definition)

    trailing_arguments_are_paths = False
    if subcommand_definition is not None:
        value_extractors.append(get_ini_value_extractor(subcommand_definition))
        trailing_arguments_are_paths = subcommand_definition.accepts_paths()
    value_extractors.append(get_default_ini_value_extractor())
    value_extractors.append(CliCanonicalValueExtractor())

    instance = create_config_object(
            subcommand,
            config_map,
            trailing_arguments,
            parser,
            ini_values,
            cli_values
        )

    if trailing_arguments_are_paths:
        instance.trailing_arguments = [
                os.fsencode(path) for path in instance.trailing_arguments
            ]

    if global_config is not None:
        global_config.debug = instance.debug

    instance.ini_path = ini_path
    return instance, subcommand_definition
