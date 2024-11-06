import shutil
import os
from typing import Dict, Optional, Any, List

from .config.config_items import ConfigItemDefinition, Context
from .subcommands import SubcommandDefinition


COMMAND = 'wordfence'


class OptionHelp:

    def __init__(
                self,
                long_name: str,
                short_name: Optional[str],
                description: str,
                category: str,
                default: str,
                valid_values: Optional[List[str]],
                context: Context,
                is_flag: bool = False,
            ):
        self.long_name = long_name
        self.short_name = short_name
        self.description = description
        self.category = category
        self.default = default
        self.valid_values = valid_values
        self.context = context
        self.is_flag = is_flag
        self.label = self.generate_label()

    def generate_label(self) -> str:
        if self.short_name is None:
            short = '   '
        else:
            short = f'-{self.short_name},'
        return f'{short} --{self.long_name}'


class LineFormatter:

    def __init__(self, terminal_size: os.terminal_size):
        self.terminal_size = terminal_size

    def split_line(
                self,
                line: str,
                max_length: int,
                offset: int = 0,
                first: bool = True
            ) -> List[str]:
        if offset > max_length:
            offset = 0
        lines = []
        while len(line) > 0:
            end = max_length - 1
            if len(line) > max_length:
                try:
                    next_break = line.rindex(' ', 0, end)
                except ValueError:
                    next_break = end
            else:
                next_break = len(line)
            next = line[:next_break]
            line = line[next_break + 1:]
            if not first:
                next = next.rjust(len(next) + offset)
            lines.append(next)
            if first:
                first = False
                max_length -= offset
        return lines

    def join_lines(
                self,
                lines: List[str],
                delimiter: str = '\n',
                offset: int = 0,
            ) -> str:
        final_lines = []
        max_length = self.terminal_size.columns
        for input_line in lines:
            initial = True
            for real_line in input_line.splitlines():
                if len(real_line) > max_length or not initial:
                    final_lines.extend(
                            self.split_line(
                                    real_line,
                                    max_length,
                                    offset,
                                    first=initial
                                )
                        )
                else:
                    final_lines.append(real_line)
                initial = False
        return delimiter.join(final_lines)

    def join_chunks(
                self,
                chunks: List[str],
                delimiter: str = '\n\n'
            ) -> str:
        return delimiter.join(chunks)


SPACER = '  '
SPACER_LENGTH = len(SPACER)


class OptionFormatter:

    def __init__(
                self,
                config_map: Dict[str, ConfigItemDefinition],
                terminal_size: os.terminal_size
            ):
        self.terminal_size = terminal_size
        self.categories = {}
        self.max_label_length = 0
        self._load_options(config_map)
        self.line_formatter = LineFormatter(terminal_size)

    def _add_option_help(self, option: OptionHelp) -> None:
        try:
            category = self.categories[option.category]
        except KeyError:
            category = {}
            self.categories[option.category] = category
        category[option.long_name] = option

    def _load_options(
                self,
                config_map: Dict[str, ConfigItemDefinition]
            ) -> None:
        for item in config_map.values():
            if item.hidden or item.context is Context.CONFIG:
                continue
            valid_values = None
            if item.has_options_list():
                valid_values = item.meta.valid_options
            option = OptionHelp(
                    item.name,
                    item.short_name,
                    item.description,
                    item.category,
                    item.default,
                    valid_values,
                    item.context,
                    item.is_flag()
                )
            self._add_option_help(option)
            self.max_label_length = max(
                    self.max_label_length,
                    len(option.label)
                )

    def _offset(self, string: str, offset: int) -> str:
        return string.rjust(offset + len(string))

    def format_category(
                self,
                title: str,
                options: Dict[str, OptionHelp]
            ) -> str:
        lines = [
                f'{title}:'
            ]
        offset = (SPACER_LENGTH * 2) + self.max_label_length
        for option in options.values():
            label = option.label.ljust(self.max_label_length)
            lines.append(
                    f'{SPACER}{label}{SPACER}{option.description}'
                )
            if option.valid_values is not None:
                valid_options = 'Options: '
                valid_options += ', '.join(option.valid_values)
                lines.append(self._offset(valid_options, offset))
            if option.is_flag and (
                        option.default or
                        option.default is None or
                        option.context is not Context.CLI
                    ):
                lines.append(self._offset(
                        f'(use --no-{option.long_name} to disable)',
                        offset
                    ))
            elif isinstance(option.default, str) and len(option.default):
                lines.append(self._offset(
                        f'(default: {option.default})',
                        offset
                    ))
        return self.line_formatter.join_lines(lines, offset=offset)

    def format_options(self) -> str:
        sections = []
        for title, options in self.categories.items():
            section = self.format_category(title, options)
            sections.append(section)
        return self.line_formatter.join_chunks(sections)


class HelpGenerator:

    def __init__(
                self,
                terminal_size: os.terminal_size
            ):
        self.terminal_size = terminal_size
        self.line_formatter = LineFormatter(terminal_size)

    def _generate_usage_details(self) -> List[str]:
        raise NotImplementedError()

    def generate_usage(self) -> str:
        details = self._generate_usage_details()
        prefix = '\n' if len(details) > 1 else ''
        usage_lines = []
        for line in details:
            usage_lines.append(f'{COMMAND} {line}')
        return prefix + '\n'.join(usage_lines)

    def _get_config_map(self) -> Dict[str, ConfigItemDefinition]:
        raise NotImplementedError()

    def generate_options(self) -> str:
        config_map = self._get_config_map()
        formatter = OptionFormatter(config_map, self.terminal_size)
        return formatter.format_options()

    def generate_description(self) -> Optional[str]:
        return None

    def generate_examples(self) -> Optional[str]:
        return None

    def generate_subcommands(self) -> Optional[str]:
        return None

    def generate_help(self) -> str:
        usage = self.generate_usage()
        description = self.generate_description()
        examples = self.generate_examples()
        options = self.generate_options()
        subcommands = self.generate_subcommands()
        sections = [
                f'Usage: {usage}'
            ]
        if description is not None and len(description) > 0:
            sections.append(description)
        if examples is not None and len(examples) > 0:
            sections.append(f'Examples:\n{examples}')
        if len(options) > 0:
            sections.append(options)
        if subcommands is not None and len(subcommands) > 0:
            sections.append(f'Subcommands:\n{subcommands}')
        return self.line_formatter.join_chunks(sections)

    def display_help(self) -> str:
        help = self.generate_help()
        print(help)


class BaseHelpGenerator(HelpGenerator):

    def __init__(
                self,
                config_map: Dict[str, ConfigItemDefinition],
                subcommand_definitions: Dict[str, SubcommandDefinition],
                terminal_size: os.terminal_size
            ):
        self.config_map = config_map
        self.subcommand_definitions = subcommand_definitions
        super().__init__(terminal_size)

    def _generate_usage_details(self) -> List[str]:
        return ['<SUBCOMMAND> [OPTIONS]']

    def _get_config_map(self) -> Dict[str, ConfigItemDefinition]:
        return self.config_map

    def generate_subcommands(self) -> Optional[str]:
        subcommands = {}
        max_name_length = 0
        for definition in self.subcommand_definitions.values():
            subcommands[definition.name] = definition.description
            max_name_length = max(len(definition.name), max_name_length)
        lines = []
        for name, description in subcommands.items():
            padded_name = name.ljust(max_name_length)
            lines.append(
                    f'{SPACER}{padded_name}{SPACER}{description}'
                )
        offset = (SPACER_LENGTH * 2) + max_name_length
        return self.line_formatter.join_lines(lines, offset=offset)


class SubcommandHelpGenerator(HelpGenerator):

    def __init__(
                self,
                definition: SubcommandDefinition,
                base_config_map: Dict[str, ConfigItemDefinition],
                terminal_size: os.terminal_size
            ):
        self.definition = definition
        self.base_config_map = base_config_map
        super().__init__(terminal_size)

    def _generate_usage_row(self, usage: str) -> str:
        return f'{self.definition.name} {usage}'

    def _generate_usage_details(self) -> List[str]:
        lines = []
        if isinstance(self.definition.usage, str):
            lines.append(self._generate_usage_row(self.definition.usage))
        else:
            for usage in self.definition.usage:
                lines.append(usage)
        return lines

    def _get_config_map(self) -> Dict[str, ConfigItemDefinition]:
        return {**self.base_config_map, **self.definition.get_config_map()}

    def generate_description(self) -> str:
        lines = [
                self.line_formatter.join_lines([self.definition.description])
            ]
        if self.definition.long_description is not None:
            lines.append(self.line_formatter.join_lines(
                        [self.definition.long_description]
                    )
                )
        return self.line_formatter.join_chunks(lines)

    def generate_examples(self) -> List[str]:
        lines = []
        if self.definition.examples is None:
            return lines
        index = 1
        for example in self.definition.examples:
            lines.append(f'{SPACER}{index}. {example.description}')
            lines.append(f'{SPACER}{SPACER}{SPACER}{example.command}')
            index += 1
        return self.line_formatter.join_lines(
                lines,
                offset=SPACER_LENGTH * 3
            )


class Helper:

    def __init__(
                self,
                subcommand_definitions: Dict[str, SubcommandDefinition],
                base_config_map: Dict[str, ConfigItemDefinition],
                terminal_size: Optional[os.terminal_size] = None
            ):
        self.subcommand_definitions = subcommand_definitions
        self.base_config_map = base_config_map
        self.terminal_size = terminal_size \
            if terminal_size is not None \
            else shutil.get_terminal_size()
        self.generators = {}

    def _initialize_generator(
                self,
                subcommand: Optional[str]
            ) -> HelpGenerator:
        if subcommand is None:
            return BaseHelpGenerator(
                    self.base_config_map,
                    self.subcommand_definitions,
                    self.terminal_size
                )
        else:
            try:
                definition = self.subcommand_definitions[subcommand]
                return SubcommandHelpGenerator(
                        definition,
                        self.base_config_map,
                        self.terminal_size
                    )
            except KeyError:
                raise ValueError(f'Invalid subcommand: {subcommand}')

    def get_generator(self, subcommand: Optional[str] = None) -> HelpGenerator:
        try:
            return self.generators[subcommand]
        except KeyError:
            generator = self._initialize_generator(subcommand)
            self.generators[subcommand] = generator
            return generator

    def _invoke_generator_method(
                self,
                subcommand: Optional[str],
                method_name: str
            ) -> Any:
        generator = self.get_generator(subcommand)
        method = getattr(generator, method_name)
        if method is None:
            raise ValueError(f'Invalid generator method: {method_name}')
        return method()

    def generate_usage(self, subcommand: Optional[str] = None) -> str:
        return self._invoke_generator_method(subcommand, 'generate_usage')

    def generate_help(self, subcommand: Optional[str] = None) -> str:
        return self._invoke_generator_method(subcommand, 'generate_help')

    def display_help(self, subcommand: Optional[str] = None) -> None:
        return self._invoke_generator_method(subcommand, 'display_help')
