import errno
import json
from argparse import Namespace
from configparser import ConfigParser
from typing import List, Set, Any, Dict

from wordfence.logging import log
from .config_items import Context, ConfigItemDefinition, CanonicalValueExtractorInterface, not_set_token, \
    get_config_map_for_subcommand, subcommand_module_map

INI_DEFAULT_FILENAME = 'wordfence-cli.ini'
INI_DEFAULT_PATH = f"/etc/wordfence/{INI_DEFAULT_FILENAME}"
valid_contexts: Set[Context] = {Context.ALL, Context.CONFIG}


class IniCanonicalValueExtractor(CanonicalValueExtractorInterface):

    def __init__(self, config_section_name):
        self.config_section_name = config_section_name

    def is_valid_source(self, source: Any) -> bool:
        return isinstance(source, ConfigParser)

    def get_canonical_value(self, definition: ConfigItemDefinition, source: ConfigParser) -> Any:
        self.assert_is_valid_source(source)

        if definition.has_ini_separator():
            # always return separated values as a string
            value = source.get(self.config_section_name, definition.property_name, fallback=not_set_token)
        elif definition.get_value_type() == bool:
            value = source.getboolean(self.config_section_name, definition.property_name, fallback=not_set_token)
        elif definition.get_value_type() == int:
            value = source.getint(self.config_section_name, definition.property_name, fallback=not_set_token)
        elif definition.get_value_type() != str:
            raise ValueError("Only string, bool, and int types are currently known to the INI parser")
        else:
            value = source.get(self.config_section_name, definition.property_name, fallback=not_set_token)
        if isinstance(value, str) and definition.has_ini_separator():
            value = value.split(definition.meta.ini_separator)
            if definition.get_value_type() == int:
                value = [int(string_int) for string_int in value]
            elif definition.get_value_type() != str:
                raise ValueError("INI files currently support lists of strings and ints, no other types")
        return value


def get_definitions(cli_values: Namespace) -> Dict[str, ConfigItemDefinition]:
    return get_config_map_for_subcommand(cli_values.subcommand)


def get_config_section_name(cli_values: Namespace) -> str:
    return subcommand_module_map[cli_values.subcommand].CONFIG_SECTION_NAME


def get_ini_value_extractor(cli_values: Namespace) -> IniCanonicalValueExtractor:
    return IniCanonicalValueExtractor(get_config_section_name(cli_values))


def get_ini_path(cli_values: Namespace) -> str:
    if 'configuration' not in cli_values or not isinstance(cli_values.configuration, str):
        return INI_DEFAULT_PATH
    return cli_values.configuration


def load_ini(cli_values) -> ConfigParser:
    config = ConfigParser()
    try:
        with open(get_ini_path(cli_values)) as file:
            config.read_file(file)
    except OSError as e:
        if e.errno == errno.EACCES:
            raise PermissionError(
                f"The current user cannot read the config file: {json.dumps(get_ini_path())}") from e
        elif e.errno != errno.ENOENT:
            raise
        # config file does not exist -- proceed with default values + CLI values
        log.warning(
            f"Config file not found or not readable: {json.dumps(get_ini_path())}. Merging default config values.")
        return config
    config_section_name = get_config_section_name(cli_values)
    definitions = get_definitions(cli_values)
    all_section_names: List[str] = config.sections()
    all_section_names.append("DEFAULT")
    invalid_settings: bool = False
    for section_name in all_section_names:
        if section_name != config_section_name:
            config.remove_section(section_name)
    # remove values that are in the incorrect context or are entirely unknown
    for property_name, value in config.items(config_section_name):
        # arguments are stored in the lookup by name (kebab-case), but written out in snake_case in the INI
        key = property_name.replace('_', '-')
        # detect unknown definitions and definitions written in kebab-case instead of snake_case
        if key not in definitions or (key == property_name and '-' in property_name):
            log.warning(f"Ignoring unknown config setting {json.dumps(property_name)}")
            config.remove_option(config_section_name, key)
            invalid_settings = True
        if key in definitions:
            valid_ini_value: bool = definitions[key].context in valid_contexts
            if not valid_ini_value:
                log.warning(
                    f"Ignoring setting that is not valid in the config file context: {json.dumps(definitions[key].name)}.")
                invalid_settings = True
                config.remove_option(config_section_name, key)
                continue
    if invalid_settings:
        log.warning("*** Invalid settings that are not known to wordfence-cli or are not intended for use in INI "
                    "config files were discarded. ***")

    return config
