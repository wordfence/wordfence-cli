from wordfence.intel.database_rules import DatabaseRuleSet, DatabaseRule
from wordfence.wordpress.database import WordpressDatabase, \
    WordpressDatabaseConnection
from ..logging import log
from typing import Union, Generator


class DatabaseScanResult:

    def __init__(
                self,
                rule: DatabaseRule,
                table: str,
                row: dict
            ):
        self.rule = rule
        self.table = table
        self.row = row


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
            ) -> Generator[DatabaseScanResult, None, None]:
        prefixed_table = connection.prefix_table(table)
        conditions = []
        rule_selects = []
        for rule in self.rule_set.get_rules(table):
            conditions.append(f'({rule.condition})')
            rule_selects.append(
                    f'WHEN {rule.condition} THEN {rule.identifier}'
                )
        rule_case = 'CASE\n' + '\n'.join(rule_selects) + '\nEND'
        query = (
                f'SELECT {rule_case} AS rule_id, {prefixed_table}.* FROM '
                f'{prefixed_table} WHERE '
                + ' OR '.join(conditions)
            )
        for result in connection.query(query):
            rule = self.rule_set.get_rule(result['rule_id'])
            del result['rule_id']
            yield DatabaseScanResult(
                    rule=rule,
                    table=table,
                    row=result
                )

    def _scan_connection(
                self,
                connection: WordpressDatabaseConnection
            ) -> Generator[DatabaseScanResult, None, None]:
        log.debug(f'Scanning database: {connection.database.debug_string}...')
        for table in self.rule_set.get_targeted_tables():
            yield from self._scan_table(connection, table)
        log.debug(f'Scan completed for: {connection.database.debug_string}')

    def scan(
                self,
                database: Union[WordpressDatabase, WordpressDatabaseConnection]
            ) -> Generator[DatabaseScanResult, None, None]:
        self.scan_count += 1
        if isinstance(database, WordpressDatabaseConnection):
            yield from self._scan_connection(database)
        else:
            log.debug(f'Connecting to database: {database.debug_string}...')
            with database.connect() as connection:
                log.debug(
                        'Successfully connected to database: '
                        f'{database.debug_string}'
                    )
                yield from self._scan_connection(connection)
