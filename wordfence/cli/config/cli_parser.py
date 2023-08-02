import argparse
import json
from argparse import ArgumentParser, Namespace
from itertools import dropwhile
from typing import Set, List, Dict, Any, Tuple

from wordfence.logging import log
from .config_items import ConfigItemDefinition, \
    CanonicalValueExtractorInterface, Context, ArgumentType, \
    not_set_token, valid_subcommands, get_config_map_for_subcommand, \
    subcommand_module_map

NAME = "Wordfence CLI"
DESCRIPTION = "Multifunction commandline tool for Wordfence"

parser: ArgumentParser = ArgumentParser(
    prog=NAME,
    description=DESCRIPTION)

valid_contexts: Set[Context] = {Context.ALL, Context.CLI}


class CliCanonicalValueExtractor(CanonicalValueExtractorInterface):
    def is_valid_source(self, source: Any) -> bool:
        return isinstance(source, Namespace)

    def get_canonical_value(self, definition: ConfigItemDefinition,
                            source: Namespace) -> Any:
        self.assert_is_valid_source(source)
        value = getattr(source, definition.property_name, not_set_token)

        # Unset repeatable options are returned as lists with a single
        # not_set_token entry. Other repeatable options with values include a
        # not_set_token entry in their list that should be discarded.
        if isinstance(value, List):
            while not_set_token in value:
                value.remove(not_set_token)
            # falsy if the list is empty, and only contained a not_set_token
            if not value:
                value = not_set_token
        return value


def add_to_parser(target_parser,
                  config_definition: ConfigItemDefinition) -> None:
    if config_definition.context not in valid_contexts:
        log.warning(
            f"Config value {json.dumps(config_definition.name)} is not a valid"
            f" CLI argument. Should it be specified in the INI file instead?")
        return
    if config_definition.name == 'help' or config_definition.short_name == 'h':
        # change this behavior by setting ArgumentParser kwarg add_help to False
        raise ValueError(
            "A help command cannot be defined, as one is added automatically"
            " by the parser")

    names: List[str] = [f"--{config_definition.name}"]
    if config_definition.short_name:
        names.append(f"-{config_definition.short_name}")

    # common arguments
    named_params: Dict[str, Any] = {
        'help': config_definition.description,
        'default': not_set_token
    }
    if config_definition.has_options_list():
        named_params['choices'] = config_definition.meta.valid_options
        named_params['type'] = config_definition.get_value_type()

    # special handling
    if config_definition.argument_type == ArgumentType.FLAG:
        # store the opposite of the default boolean
        named_params['action'] = 'store_true'
        # adjust the provided help message
        defaults_to = f'true (--{config_definition.name})' if (
            config_definition.default) else \
            f'false (--no-{config_definition.name})'
        named_params['help'] += f' If not specified, defaults to {defaults_to}.'
    elif config_definition.argument_type == ArgumentType.OPTION_REPEATABLE:
        named_params['action'] = 'append'
        named_params['default'] = [not_set_token]
        named_params['type'] = config_definition.get_value_type()

    if config_definition.hidden:
        named_params['help'] = argparse.SUPPRESS

    target_parser.add_argument(*names, **named_params)

    # register the negation of a flag
    if config_definition.argument_type == ArgumentType.FLAG:
        named_params['action'] = 'store_false'
        names = [f"--no-{config_definition.name}"]
        if config_definition.hidden:
            named_params['help'] = argparse.SUPPRESS
        else:
            del named_params['help']
        # set the value to override the un-prefixed command
        named_params['dest'] = config_definition.property_name
        target_parser.add_argument(*names, **named_params)


class DropWhilePredicate:
    def __init__(self):
        self.drop_next: bool = True

    def __call__(self, entry: str) -> bool:
        if not self.drop_next:
            return False
        if '--' == entry:
            self.drop_next = False
        return True


def get_cli_values() -> Tuple[Namespace, List[str]]:
    subparsers = parser.add_subparsers(title="Wordfence CLI subcommands",
                                       dest="subcommand")
    for subcommand in valid_subcommands:
        definitions = get_config_map_for_subcommand(subcommand)
        subparser = subparsers.add_parser(subcommand,
                                          prog=subcommand_module_map[
                                              subcommand].CLI_TITLE)
        for definition in definitions.values():
            add_to_parser(subparser, definition)

    cli_values, trailing_arguments = parser.parse_known_args()
    trailing_arguments = list(
        dropwhile(DropWhilePredicate(), trailing_arguments))
    return cli_values, trailing_arguments
