import sys
import os
import logging

from ..version import __version__, __version_name__
from ..util import pcre, updater
from ..util.caching import Cache, CacheDirectory, RuntimeCache, \
        CacheException
from ..logging import log
from ..scanning.scanner import ExceptionContainer
from .banner.banner import show_welcome_banner_if_enabled
from .config import load_config
from .subcommands import load_subcommand_definitions
from .context import CliContext
from .configure import Configurer
from .terms import TermsManager


class WordfenceCli:

    def __init__(self):
        self.subcommand_definitions = load_subcommand_definitions()
        self.config, self.subcommand_definition = load_config(
                self.subcommand_definitions
            )
        self.initialize_logging()
        self.cache = self.initialize_cache()
        self.subcommand = None

    def print_error(self, message: str) -> None:
        if sys.stderr is not None:
            print(message, file=sys.stderr)
        else:
            print(message)

    def initialize_logging(self) -> None:
        if self.config.quiet:
            log.setLevel(logging.CRITICAL)
        elif self.config.debug:
            log.setLevel(logging.DEBUG)
        elif self.config.verbose or (
                    self.config.verbose is None
                    and sys.stdout is not None and sys.stdout.isatty()
                ):
            log.setLevel(logging.INFO)

    def initialize_cache(self) -> Cache:
        cacheable_types = set()
        for definition in self.subcommand_definitions.values():
            cacheable_types.update(definition.cacheable_types)
        if self.config.cache:
            try:
                return CacheDirectory(
                        os.path.expanduser(self.config.cache_directory),
                        cacheable_types
                    )
            except CacheException as exception:
                log.warning(
                        'Failed to initialize directory cache: '
                        + str(exception)
                    )
        return RuntimeCache()

    def display_version(self) -> None:
        print(f"Wordfence CLI {__version__} \"{__version_name__}\"")
        jit_support_text = 'Yes' if pcre.HAS_JIT_SUPPORT else 'No'
        print(
                f"PCRE Version: {pcre.VERSION} - "
                f"JIT Supported: {jit_support_text}"
            )

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

    def invoke(self) -> int:
        if self.config.purge_cache:
            self.cache.purge()

        show_welcome_banner_if_enabled(self.config)

        if self.config.version:
            self.display_version()
            return 0

        if self.config.check_for_update:
            updater.Version.check(self.cache)

        context = CliContext(
                self.config,
                self.cache
            )

        terms_manager = TermsManager(context)
        context.register_terms_update_hook(terms_manager.trigger_update)

        configurer = Configurer(
                self.config,
                terms_manager,
                self.subcommand_definition
            )
        configurer.check_config()

        if self.subcommand_definition is None:
            if not configurer.written:
                self.config.display_help()
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
    cli = WordfenceCli()
    exit_code = cli.invoke()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
