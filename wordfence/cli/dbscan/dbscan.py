from wordfence.wordpress.database import WordpressDatabase, \
    WordpressDatabaseServer
from wordfence.intel.database_rules import DatabaseRuleSet
from wordfence.databasescanning.scanner import DatabaseScanner
from getpass import getpass
from typing import Optional
import os

from ...logging import log
from ..subcommands import Subcommand


class DbScanSubcommand(Subcommand):

    def resolve_password(self) -> Optional[str]:
        if self.config.password is not None:
            log.warning(
                    'Providing passwords via command line parameters is '
                    'insecure as they can be exposed to other users'
                )
            return self.config.password
        elif self.config.prompt_for_password:
            return getpass()
        return os.environ.get(self.config.password_env)

    def invoke(self) -> int:
        ruleSet = DatabaseRuleSet()
        scanner = DatabaseScanner(ruleSet)
        server = WordpressDatabaseServer(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.resolve_password()
            )
        for database_name in self.config.trailing_arguments:
            database = WordpressDatabase(
                    name=database_name,
                    server=server
                )
            scanner.scan(database)
        return 0


factory = DbScanSubcommand
