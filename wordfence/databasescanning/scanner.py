from wordfence.intel.database_rules import DatabaseRuleSet
from wordfence.wordpress.database import WordpressDatabase, \
    WordpressDatabaseConnection
from ..logging import log
from typing import Union


class DatabaseScanner:

    def __init__(
                self,
                rule_set: DatabaseRuleSet
            ):
        self.rule_set = rule_set
        self.scan_count = 0

    def _scan_table(
                self,
                connection: WordpressDatabaseConnection,
                table: str
            ):
        pass

    def _scan_connection(
                self,
                connection: WordpressDatabaseConnection
            ) -> None:
        log.debug(f'Scanning database: {connection.database.debug_string}...')
        pass
        log.debug(f'Scan completed for: {connection.database.debug_string}...')

    def scan(
                self,
                database: Union[WordpressDatabase, WordpressDatabaseConnection]
            ) -> None:
        self.scan_count += 1
        if isinstance(database, WordpressDatabaseConnection):
            return self._scan_connection(database)
        else:
            log.debug(f'Connecting to database: {database.debug_string}...')
            with database.connect() as connection:
                log.debug(
                        'Successfully connected to database: '
                        f'{database.debug_string}'
                    )
                return self._scan_connection(connection)
