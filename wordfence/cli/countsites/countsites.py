import os
from ...wordpress.site import WordpressLocator
from ...logging import log
from ..subcommands import Subcommand
from ..io import IoManager
from ..exceptions import ConfigurationException


class CountSitesSubcommand(Subcommand):

    def count_sites(self, path: bytes) -> int:
        count = 0
        locator = WordpressLocator(
                    path=path,
                    allow_nested=self.config.allow_nested,
                    allow_io_errors=self.config.allow_io_errors
                )
        for core in locator.locate_core_paths():
            log.debug('Located WordPress site at ' + os.fsdecode(core))
            count += 1
        return count

    def invoke(self) -> int:
        count = 0
        paths_counted = 0
        io_manager = IoManager(
                self.config.read_stdin,
                self.config.path_separator,
                binary=True
            )
        for path in self.config.trailing_arguments:
            count += self.count_sites(path)
            paths_counted += 1
        if io_manager.should_read_stdin():
            for path in io_manager.get_input_reader().read_all_entries():
                count += self.count_sites(path)
                paths_counted += 1
        if self.context.requires_input(self.config.require_path) \
                and paths_counted == 0:
            raise ConfigurationException(
                    'At least one path must be specified'
                )
        log.info(f'Located {count} WordPress site(s)')
        print(count)
        return 0


factory = CountSitesSubcommand
