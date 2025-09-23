from __future__ import annotations

import argparse
import json
import os
from argparse import ArgumentParser, Namespace
from typing import TYPE_CHECKING, Set, List, Dict, Any, Tuple

from wordfence.logging import log
from .config_items import ConfigItemDefinition, \
    CanonicalValueExtractorInterface, Context, ArgumentType, \
    not_set_token
from .base_config_definitions \
        import config_map as base_config_map

if TYPE_CHECKING:
    from ..helper import Helper
    from ..subcommands import SubcommandDefinition

NAME = "Wordfence CLI"
DESCRIPTION = ("Multifunction commandline tool for Wordfence - "
               "use wordfence {subcommand} --help for additional"
               " information about subcommands"
               )
COMMAND = "wordfence"

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

    def get_context(self) -> Context:
        return Context.CLI


def create_split_and_append_action(delimiter: str, value_type=None):

    if value_type is None:
        value_type = str

    class SplitAndAppend(argparse.Action):

        def __call__(
                    self,
                    parser: argparse.ArgumentParser,
                    namespace: argparse.Namespace,
                    values,
                    option_string=None
                ):
            items = getattr(namespace, self.dest, [])
            new_values = values.split(delimiter)
            items.extend(
                    [value_type(value) for value in new_values if value != '']
                )
            setattr(namespace, self.dest, items)

    return SplitAndAppend


def add_to_parser(target_parser,
                  config_definition: ConfigItemDefinition) -> None:
    if config_definition.context not in valid_contexts:
        log.warning(
            f"Config value {json.dumps(config_definition.name)} is not a valid"
            f" CLI argument. Should it be specified in the INI file instead?")
        return

    names: List[str] = [f"--{config_definition.name}"]
    if config_definition.short_name:
        names.append(f"-{config_definition.short_name}")

    # common arguments
    named_params: Dict[str, Any] = {
        'help': config_definition.description,
        'default': not_set_token,
        'action': 'store'
    }
    if config_definition.has_options_list():
        named_params['choices'] = config_definition.meta.valid_options

    # special handling
    if config_definition.is_flag():
        # store the opposite of the default boolean
        named_params['action'] = 'store_true'
        # adjust the provided help message
        defaults_to = f'true (--{config_definition.name})' if (
            config_definition.default) else \
            f'false (--no-{config_definition.name})'
        if config_definition.argument_type == ArgumentType.FLAG \
                and config_definition.default:
            named_params['help'] += (f' If not specified, defaults to '
                                     f'{defaults_to}.')
    elif config_definition.argument_type == ArgumentType.OPTION_REPEATABLE:
        named_params['action'] = 'append'
        named_params['default'] = [not_set_token]

    if config_definition.has_separator():
        named_params['default'] = [not_set_token]
        named_params['action'] = \
            create_split_and_append_action(
                    config_definition.meta.separator,
                    config_definition.get_value_type()
                )
    # store_true and store_false do not have the same options as other actions,
    # and will throw an error if type is specified
    elif not isinstance(named_params['action'], str) or \
            not named_params['action'].startswith('store_'):
        if config_definition.accepts_paths():
            named_params['type'] = os.fsencode
        else:
            named_params['type'] = config_definition.get_value_type()

    named_params['help'] = argparse.SUPPRESS

    target_parser.add_argument(*names, **named_params)

    # register the negation of a flag
    if config_definition.is_flag():
        named_params['action'] = 'store_false'
        names = [f"--no-{config_definition.name}"]
        named_params['help'] = argparse.SUPPRESS
        # set the value to override the un-prefixed command
        named_params['dest'] = config_definition.property_name
        target_parser.add_argument(*names, **named_params)


def add_definitions_to_parser(
            parser: ArgumentParser,
            definitions: Dict[str, ConfigItemDefinition]
        ) -> None:
    for definition in definitions.values():
        add_to_parser(parser, definition)


def get_cli_values(
            subcommand_definitions: Dict[str, 'SubcommandDefinition'],
            helper: 'Helper'
        ) -> Tuple[Namespace, List[str], ArgumentParser]:
    parser = ArgumentParser(
            prog=COMMAND,
            description=DESCRIPTION,
            add_help=False,
            usage=helper.generate_usage()
        )

    add_definitions_to_parser(parser, base_config_map)

    subparsers = parser.add_subparsers(title="Available Subcommands",
                                       dest="subcommand",
                                       metavar='')
    for subcommand_definition in subcommand_definitions.values():
        definitions = subcommand_definition.get_config_map()
        subparser = subparsers.add_parser(
                subcommand_definition.name,
                prog=subcommand_definition.name,
                add_help=False,
                usage=helper.generate_usage(),
            )
        add_definitions_to_parser(subparser, base_config_map)
        add_definitions_to_parser(subparser, definitions)

        for previous_name in subcommand_definition.previous_names:
            subparsers.add_parser(
                    previous_name,
                    prog=previous_name
                )

    cli_values, trailing_arguments = parser.parse_known_args()
    if '--' in trailing_arguments:
        if trailing_arguments[0] != '--':
            unknowns = trailing_arguments[0:trailing_arguments.index('--')]
            unknowns = ', '.join(map(lambda x: json.dumps(x), unknowns))
            raise ValueError(f"Encountered unknown command arguments: "
                             f"{unknowns}")
        trailing_arguments = trailing_arguments[1:]
    return cli_values, trailing_arguments, parser
