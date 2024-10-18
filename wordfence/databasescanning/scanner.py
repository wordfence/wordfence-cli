from typing import Union, Generator, List
from wordfence.intel.database_rules import DatabaseRuleSet, DatabaseRule
from wordfence.wordpress.database import WordpressDatabase, \
    WordpressDatabaseConnection
from wordfence.logging import log, VERBOSE
from wordfence.util.timing import Timer


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
        self.timer = Timer(start=False)

    def _get_valid_columns(
                self,
                connection: WordpressDatabaseConnection,
                prefixed_table: str
            ) -> List:
        columns = connection.get_column_types(prefixed_table)
        try:
            del columns['rule_id']
        except KeyError:
            pass  # If the column doesn't exist, that's fine
        return list(columns.keys())

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
        selected_columns = self._get_valid_columns(connection, prefixed_table)
        selected_columns.append(f'{rule_case} as rule_id')
        selected_columns = ', '.join(selected_columns)
        query = (
                f'SELECT {selected_columns} FROM '
                f'{prefixed_table} WHERE '
                + ' OR '.join(conditions)
            )
        # Using a dict as the query parameters avoids %s from being
        # interpreted as a placeholder (there is apparently no way
        # to escape "%s" ("%%s" doesn't work)
        for result in connection.query_literal(query):
            rule = self.rule_set.get_rule(result['rule_id'])
            del result['rule_id']
            yield DatabaseScanResult(
                    rule=rule,
                    table=prefixed_table,
                    row=result
                )

    def _scan_connection(
                self,
                connection: WordpressDatabaseConnection
            ) -> Generator[DatabaseScanResult, None, None]:
        self.timer.resume()
        log.log(
                VERBOSE,
                f'Scanning database: {connection.database.debug_string}...'
            )
        for table in self.rule_set.get_targeted_tables():
            yield from self._scan_table(connection, table)
        log.log(
                VERBOSE,
                f'Scan completed for: {connection.database.debug_string}'
            )
        self.timer.stop()

    def scan(
                self,
                database: Union[WordpressDatabase, WordpressDatabaseConnection]
            ) -> Generator[DatabaseScanResult, None, None]:
        self.scan_count += 1
        if isinstance(database, WordpressDatabaseConnection):
            yield from self._scan_connection(database)
        else:
            log.log(
                    VERBOSE,
                    f'Connecting to database: {database.debug_string}...'
                )
            with database.connect() as connection:
                log.log(
                        VERBOSE,
                        'Successfully connected to database: '
                        f'{database.debug_string}'
                    )
                yield from self._scan_connection(connection)

    def get_elapsed_time(self) -> int:
        return self.timer.get_elapsed()
