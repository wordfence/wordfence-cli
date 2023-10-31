import sys
import logging

from ..util import updater
from ..util.caching import Cache, CacheDirectory, RuntimeCache, \
        CacheException
from ..util.terminal import supports_colors
from ..util.io import resolve_path
from ..logging import log, enable_log_colors, VERBOSE
from ..scanning.scanner import ExceptionContainer
from .banner.banner import show_welcome_banner_if_enabled
from .config import load_config, RenamedSubcommandException
from .config.base_config_definitions import config_map \
        as base_config_map
from .subcommands import load_subcommand_definitions
from .context import CliContext
from .configurer import Configurer
from .terms import TermsManager
from .helper import Helper


class WordfenceCli:

    def __init__(self):
        self.initialize_early_logging()
        self.subcommand_definitions = load_subcommand_definitions()
        self.helper = self._initialize_helper()
        self._load_config()
        self.allows_color = self.config.color is not False \
            and supports_colors()
        self.initialize_logging(self.config.verbose)
        self.cache = self.initialize_cache()
        self.subcommand = None

    def _initialize_helper(self) -> Helper:
        return Helper(
                self.subcommand_definitions,
                base_config_map
            )

    def _load_config(self) -> None:
        try:
            self.config, self.subcommand_definition = load_config(
                    self.subcommand_definitions,
                    self.helper
                )
        except RenamedSubcommandException as rename:
            print(
                    f'The "{rename.old}" subcommand has been renamed to '
                    f'"{rename.new}"'
                )
            sys.exit(1)

    def print_error(self, message: str) -> None:
        if sys.stderr is not None:
            print(message, file=sys.stderr)
        else:
            print(message)

    def initialize_early_logging(self) -> None:
        log.setLevel(logging.INFO)

    def initialize_logging(self, verbose: bool = False) -> None:
        if self.config.quiet:
            log.setLevel(logging.CRITICAL)
        elif self.config.debug:
            log.setLevel(logging.DEBUG)
        elif self.config.verbose or (
                    self.config.verbose is None
                    and sys.stdout is not None and sys.stdout.isatty()
                ):
            log.setLevel(VERBOSE)
        else:
            log.setLevel(logging.INFO)
        if self.allows_color:
            enable_log_colors()

    def initialize_cache(self) -> Cache:
        cacheable_types = set()
        for definition in self.subcommand_definitions.values():
            cacheable_types.update(definition.cacheable_types)
        if self.config.cache:
            try:
                return CacheDirectory(
                        resolve_path(self.config.cache_directory),
                        cacheable_types
                    )
            except CacheException as exception:
                log.warning(
                        'Failed to initialize directory cache: '
                        + str(exception)
                    )
        return RuntimeCache()

    def process_exception(self, exception: BaseException) -> int:
        if isinstance(exception, ExceptionContainer):
            if self.config.debug:
                self.print_error(exception.trace)
                return 1
            exception = exception.exception
        if self.config.debug:
            raise exception
        else:
            if isinstance(exception, SystemExit):
                raise exception
            else:
                if self.subcommand is None:
                    message = None
                else:
                    message = self.subcommand.generate_exception_message(
                            exception
                        )
                if message is None:
                    message = f'Error: {exception}'
                self.print_error(message)
        return 1

    def display_help(self) -> None:
        self.helper.display_help(self.config.subcommand)

    def invoke(self) -> int:
        if self.config.purge_cache:
            self.cache.purge()

        show_welcome_banner_if_enabled(self.config)

        if self.config.help:
            self.display_help()
            return 0

        context = CliContext(
                self.config,
                self.cache,
                self.helper,
                self.allows_color
            )

        if self.config.version:
            context.display_version()
            return 0

        if self.config.check_for_update:
            updater.Version.check(self.cache)

        terms_manager = TermsManager(context)
        context.register_terms_update_hook(terms_manager.trigger_update)

        configurer = Configurer(
                self.config,
                self.helper,
                terms_manager,
                self.subcommand_definitions,
                self.subcommand_definition
            )
        context.configurer = configurer

        if self.subcommand_definition is None:
            self.display_help()
            configurer.check_config()
            return 0

        if self.subcommand_definition.requires_config \
                and not configurer.check_config():
            return 0

        self.subcommand = None
        try:
            self.subcommand = self.subcommand_definition.initialize_subcommand(
                    context
                )
            return self.subcommand.invoke()
        except BaseException as exception:
            if self.subcommand is not None:
                self.subcommand.terminate()
            return self.process_exception(exception)


def main():
    try:
        cli = WordfenceCli()
        exit_code = cli.invoke()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == '__main__':
    main()
