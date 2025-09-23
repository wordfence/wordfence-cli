from __future__ import annotations

import errno
import json
import os

from argparse import Namespace
from configparser import ConfigParser, NoSectionError
from typing import TYPE_CHECKING, List, Set, Any, Callable, Optional

from wordfence.logging import log
from .config_items import Context, ConfigItemDefinition, \
    CanonicalValueExtractorInterface, not_set_token, \
    ReferenceToken, merge_config_maps
from .defaults import INI_DEFAULT_PATH
from .base_config_definitions import config_map as base_config_map

if TYPE_CHECKING:
    from ..subcommands import SubcommandDefinition


valid_contexts: Set[Context] = {Context.ALL, Context.CONFIG}


GLOBAL_INI_PATH = b'/etc/wordfence/wordfence-cli.ini'
DEFAULT_SECTION_NAME = 'DEFAULT'


class IniCanonicalValueExtractor(CanonicalValueExtractorInterface):

    def __init__(self, *config_section_names):
        self.config_section_names = config_section_names

    def is_valid_source(self, source: Any) -> bool:
        return isinstance(source, ConfigParser)

    def _get_value_from_section(
                self,
                definition: ConfigItemDefinition,
                source: ConfigParser,
                section: str
            ) -> Any:
        if definition.has_separator():
            # always return separated values as a string
            return source.get(
                    section,
                    definition.property_name,
                    fallback=not_set_token
                )
        elif definition.get_value_type() == bool:
            return source.getboolean(
                    section,
                    definition.property_name,
                    fallback=not_set_token
                )
        elif definition.get_value_type() == int:
            return source.getint(
                    section,
                    definition.property_name,
                    fallback=not_set_token
                )
        elif definition.accepts_paths():
            path = source.get(
                    section,
                    definition.property_name,
                    fallback=not_set_token
                )
            if path != not_set_token:
                path = os.fsencode(path)
            return path
        elif isinstance(definition.get_value_type(), Callable):
            value = source.get(
                    section,
                    definition.property_name,
                    fallback=not_set_token
                )
            # convert using the type method
            value = value if isinstance(value, ReferenceToken) else (
                (definition.get_value_type())(value))
            return value
        elif definition.get_value_type() != str:
            raise ValueError(
                    "Only string, bool, int, and callable types are currently "
                    "known to the INI parser"
                )
        else:
            return source.get(
                    section,
                    definition.property_name,
                    fallback=not_set_token
                )

    def get_canonical_value(self, definition: ConfigItemDefinition,
                            source: ConfigParser) -> Any:
        self.assert_is_valid_source(source)

        for section in self.config_section_names:
            value = self._get_value_from_section(
                    definition,
                    source,
                    section
                )
            if value is not None and value is not not_set_token:
                break

        if isinstance(value, str) and definition.has_separator():
            value = value.split(definition.meta.separator)
            if definition.get_value_type() == int:
                value = [int(string_int) for string_int in value]
            elif definition.get_value_type() != str:
                raise ValueError(
                    "INI files currently support lists of strings and ints, no"
                    " other types")

        return value

    def get_context(self) -> Context:
        return Context.CONFIG


def get_ini_value_extractor(
            subcommand_definition: 'SubcommandDefinition'
        ) -> IniCanonicalValueExtractor:
    return IniCanonicalValueExtractor(
            subcommand_definition.config_section,
            DEFAULT_SECTION_NAME
        )


def get_default_ini_value_extractor() -> IniCanonicalValueExtractor:
    return IniCanonicalValueExtractor(DEFAULT_SECTION_NAME)


def get_ini_path(cli_values: Namespace) -> str:
    if 'configuration' not in cli_values or not isinstance(
            cli_values.configuration, bytes):
        path = INI_DEFAULT_PATH
    else:
        path = cli_values.configuration
    return os.path.expanduser(path)


def load_ini(
            cli_values,
            subcommand_definition: Optional['SubcommandDefinition']
        ) -> (ConfigParser, Optional[str]):
    config = ConfigParser()
    try:
        with open(GLOBAL_INI_PATH, 'r') as file:
            config.read_file(file)
    except FileNotFoundError:
        pass  # Ignore nonexistant global config files
    except OSError:
        log.warning(f'Failed to read global config file at {GLOBAL_INI_PATH}')
    ini_path = get_ini_path(cli_values)
    try:
        with open(ini_path) as file:
            config.read_file(file)
    except OSError as e:
        if e.errno == errno.EACCES:
            raise PermissionError(
                f"The current user cannot read the config file: "
                f"{json.dumps(get_ini_path(cli_values))}") from e
        elif e.errno != errno.ENOENT:
            raise
        # config file does not exist: proceed with default values + CLI values
        return (config, None)
    section_map = {
            DEFAULT_SECTION_NAME: base_config_map,
        }
    if subcommand_definition is not None:
        section_map[subcommand_definition.config_section] = \
                merge_config_maps(
                        base_config_map,
                        subcommand_definition.get_config_map()
                    )
    all_section_names: List[str] = config.sections()
    invalid_settings: bool = False
    for section_name in all_section_names:
        if section_name not in section_map:
            config.remove_section(section_name)
    # remove values that are in the incorrect context or are entirely unknown
    for section, definitions in section_map.items():
        try:
            items = config.items(section)
        except NoSectionError:
            items = {}
        for property_name, _value in items:
            # arguments are stored in the lookup by name (kebab-case), but
            # written out in snake_case in the INI
            key = property_name.replace('_', '-')
            # detect unknown definitions and definitions written in kebab-case
            # instead of snake_case
            if key not in definitions or (
                    key == property_name and '-' in property_name):
                log.warning(
                        "Ignoring unknown config setting "
                        f"{json.dumps(property_name)}"
                    )
                config.remove_option(section, property_name)
                invalid_settings = True
            if key in definitions:
                valid_ini_value = definitions[key].context in valid_contexts
                if not valid_ini_value:
                    log.warning(
                        f"Ignoring setting that is not valid in the config "
                        f"file context: {json.dumps(definitions[key].name)}.")
                    invalid_settings = True
                    config.remove_option(section, property_name)
                    continue
    if invalid_settings:
        log.warning(
            "*** Invalid settings not known to wordfence-cli or that are not "
            "intended for use in INI config files were discarded. ***")

    return (config, ini_path)
