import sys
import logging
from typing import Set

from ..util import updater
from ..util.terminal import supports_colors
from ..logging import log
from ..scanning.scanner import ExceptionContainer
from .banner.banner import show_welcome_banner_if_enabled
from .config import load_config, RenamedSubcommandException, GlobalConfig
from .config.base_config_definitions import config_map \
        as base_config_map
from .subcommands import load_subcommand_definitions
from .context import CliContext
from .configurer import Configurer
from . import licensing
from .terms_management import TermsManager
from .import terms_management
from .helper import Helper


class ExceptionHandler:

    def __init__(self):
        self.global_config = GlobalConfig()
        self.subcommand = None

    def print_error(self, message: str) -> None:
        if sys.stderr is not None:
            print(message, file=sys.stderr)
        else:
            print(message)

    def process_exception(self, exception: BaseException) -> int:
        if self.subcommand is not None:
            self.subcommand.terminate()
        if isinstance(exception, ExceptionContainer):
            if self.global_config.debug:
                self.print_error(exception.trace)
                return 1
            exception = exception.exception
        if self.global_config.debug:
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


class WordfenceCli:

    def __init__(self, exception_handler: ExceptionHandler):
        self.exception_handler = exception_handler
        self.initialize_early_logging()
        self.subcommand_definitions = load_subcommand_definitions()
        self.helper = self._initialize_helper()
        self._load_config(exception_handler)
        self.allows_color = self.config.color is not False \
            and supports_colors()

    def _initialize_helper(self) -> Helper:
        return Helper(
                self.subcommand_definitions,
                base_config_map
            )

    def _load_config(self, exception_handler: ExceptionHandler) -> None:
        try:
            self.config, self.subcommand_definition = load_config(
                    self.subcommand_definitions,
                    self.helper,
                    global_config=exception_handler.global_config
                )
        except RenamedSubcommandException as rename:
            print(
                    f'The "{rename.old}" subcommand has been renamed to '
                    f'"{rename.new}"'
                )
            sys.exit(1)

    def initialize_early_logging(self) -> None:
        log.setLevel(logging.INFO)

    def _get_cacheable_types(self) -> Set[str]:
        cacheable_types = set()
        cacheable_types.update(licensing.CACHEABLE_TYPES)
        cacheable_types.update(terms_management.CACHEABLE_TYPES)
        for definition in self.subcommand_definitions.values():
            cacheable_types.update(definition.cacheable_types)
        return cacheable_types

    def display_help(self) -> None:
        self.helper.display_help(self.config.subcommand)

    def configure_stdio(self) -> bool:
        original_encoding = sys.stdout.encoding
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
        if original_encoding != 'utf-8':
            log.warning(
                    f'Encoding for stdout is {original_encoding} instead of '
                    'utf-8'
                )
            return True
        else:
            return False

    def invoke(self) -> int:
        with CliContext(
                    self.config,
                    self._get_cacheable_types(),
                    self.helper,
                    self.allows_color
                ) as context:
            context.initialize_logging()
            stdio_changed = self.configure_stdio()

            if self.config.purge_cache:
                context.cache.purge()

            if not stdio_changed:
                show_welcome_banner_if_enabled(self.config)

            if self.config.help:
                self.display_help()
                return 0

            if self.config.version:
                context.display_version()
                return 0

            if self.config.check_for_update:
                updater.Version.check(context.cache)

            license_manager = licensing.LicenseManager(context)
            context.register_license_update_hook(
                    license_manager.update_license
                )

            terms_manager = TermsManager(context, license_manager)
            context.register_terms_update_hook(terms_manager.trigger_update)

            configurer = Configurer(
                    context,
                    self.helper,
                    license_manager,
                    terms_manager,
                    self.subcommand_definitions,
                    self.subcommand_definition
                )
            context.configurer = configurer

            if self.subcommand_definition is None:
                self.display_help()
                configurer.check_config()
                return 0

            if self.subcommand_definition.requires_config:
                if not configurer.check_config():
                    return 0
                if not self.subcommand_definition.uses_license:
                    license_manager.check_license()
                terms_manager.prompt_acceptance_if_needed()

            subcommand = self.subcommand_definition.initialize_subcommand(
                    context
                )
            self.exception_handler.subcommand = subcommand
            return subcommand.invoke()


def invoke_cli():
    exception_handler = ExceptionHandler()
    try:
        cli = WordfenceCli(exception_handler)
        return cli.invoke()
    except BaseException as exception:  # noqa: B036
        return exception_handler.process_exception(exception)
    except KeyboardInterrupt:
        return 130


def main():
    exit_code = invoke_cli()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
