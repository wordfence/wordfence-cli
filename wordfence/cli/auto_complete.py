import sys
from typing import List, Iterable, Dict, Optional

from .config import resolve_config_map
from .config.config_items import ConfigItemDefinition
from .subcommands import SubcommandDefinition, load_subcommand_definition, \
        VALID_SUBCOMMANDS


def _write_bool(value: bool) -> None:
    print('true' if value else '')


def _write_options(
            options: Iterable[str],
            allow_files: bool = False,
            allow_directories: bool = False
        ) -> None:
    print(' '.join(options))
    _write_bool(allow_files)
    _write_bool(allow_directories)


def _write_completion_options(
            words: List[str],
            subcommand_definition: SubcommandDefinition,
            config_map: Dict[str, ConfigItemDefinition],
            previous: Optional[str] = None
        ) -> bool:
    options = []
    allow_files = subcommand_definition.accepts_files
    allow_directories = subcommand_definition.accepts_directories
    if subcommand_definition.name == 'help':
        options.extend(VALID_SUBCOMMANDS)
    for item in config_map.values():
        item_options = {
                f'--{item.name}'
            }
        if item.short_name is not None:
            item_options.add(f'-{item.short_name}')
        if item.is_flag():
            item_options.add(f'--no-{item.name}')
        if previous in item_options and item.accepts_value():
            options = [] if item.meta.valid_options is None \
                else list(item.meta.valid_options)
            allow_files = item.meta.accepts_file
            allow_directories = item.meta.accepts_directory
            break
        options.extend(item_options)
    _write_options(
            options,
            allow_files,
            allow_directories
        )


def auto_complete(words: List[str], cursor_index: int) -> None:
    try:
        subcommand = words[1]
    except IndexError:
        subcommand = None
    # cursor_word = words[cursor_index]
    if cursor_index == 1 or subcommand is None:
        _write_options(VALID_SUBCOMMANDS)
    else:
        subcommand_definition = load_subcommand_definition(subcommand)
        config_map = resolve_config_map(subcommand_definition)
        try:
            previous = words[cursor_index - 1]
        except IndexError:
            previous = None
        _write_completion_options(
                words,
                subcommand_definition,
                config_map,
                previous
            )


if __name__ == '__main__':
    words = sys.argv[1:-1]
    index = sys.argv[-1]
    if not index.isdecimal():
        raise Exception('Cursor index must be a number')
    index = int(index)
    auto_complete(words, index)
