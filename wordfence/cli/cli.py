import sys
import os
import logging
from typing import Dict

from ..version import __version__
from ..util import pcre, updater
from ..util.caching import Cache, CacheDirectory, RuntimeCache, \
        CacheException
from ..logging import log
from ..scanning.scanner import ExceptionContainer
from .banner.banner import show_welcome_banner_if_enabled
from .config import Config, load_config
from .subcommands import SubcommandDefinition, load_subcommand_definitions
from .context import CliContext
from .configure import Configurer
from .scan.progress import ProgressException  # TODO


def print_error(message: str) -> None:
    if sys.stderr is not None:
        print(message, file=sys.stderr)
    else:
        print(message)


def initialize_logging(config: Config) -> None:
    if config.quiet:
        log.setLevel(logging.CRITICAL)
    elif config.debug:
        log.setLevel(logging.DEBUG)
    elif config.verbose or (
                config.verbose is None
                and sys.stdout is not None and sys.stdout.isatty()
            ):
        log.setLevel(logging.INFO)


def initialize_cache(
            config: Config,
            subcommand_definitions: Dict[str, SubcommandDefinition]
        ) -> Cache:
    cacheable_types = set()
    for definition in subcommand_definitions.values():
        cacheable_types.update(definition.cacheable_types)
    if config.cache:
        try:
            return CacheDirectory(
                    os.path.expanduser(config.cache_directory)
                )
        except CacheException as exception:
            log.warning(
                    'Failed to initialize directory cache: ' + str(exception)
                )
    return RuntimeCache()


def display_version() -> None:
    print(f"Wordfence CLI {__version__}")
    jit_support_text = 'Yes' if pcre.HAS_JIT_SUPPORT else 'No'
    print(f"PCRE Version: {pcre.VERSION} - JIT Supported: {jit_support_text}")


def process_exception(exception: BaseException, config: Config) -> int:
    if isinstance(exception, ExceptionContainer):
        if config.debug:
            print_error(exception.trace)
            return 1
        exception = exception.exception
    if config.debug:
        raise exception
    else:
        if isinstance(exception, ProgressException):
            print_error(
                    'The current terminal size is inadequate for '
                    'displaying progress output for the current scan '
                    'options'
                )
        elif isinstance(exception, SystemExit):
            raise exception
        else:
            print_error(f'Error: {exception}')
    return 1


def main() -> int:
    subcommand_definitions = load_subcommand_definitions()

    config, subcommand_definition = load_config(subcommand_definitions)

    initialize_logging(config)

    cache = initialize_cache(
            config,
            subcommand_definitions
        )

    if config.purge_cache:
        cache.purge()

    show_welcome_banner_if_enabled(config)

    if config.version:
        display_version()
        return 0

    if config.check_for_update:
        updater.Version.check(cache)

    if subcommand_definition is None:
        config.display_help()
        return 0

    configurer = Configurer(config)
    configurer.check_config()

    context = CliContext(
            config,
            cache
        )

    subcommand = None
    try:
        subcommand = subcommand_definition.initialize_subcommand(context)
        return subcommand.invoke()
    except BaseException as exception:
        if subcommand is not None:
            subcommand.terminate()
        return process_exception(exception, config)


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
