import pymysql
from typing import Optional, Generator, Dict, Any

from .exceptions import WordpressDatabaseException


DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 3306
DEFAULT_USER = 'root'
DEFAULT_PREFIX = 'wp_'
DEFAULT_COLLATION = 'utf8mb4_unicode_ci'


class WordpressDatabaseConnection:

    def __init__(self, database):
        self.database = database
        try:
            self.connection = pymysql.connect(
                    host=database.server.host,
                    port=database.server.port,
                    user=database.server.user,
                    password=database.server.password,
                    database=database.name
                )
            self.set_collation(database.collation)
        except pymysql.MySQLError:
            raise WordpressDatabaseException(
                    database,
                    f'Failed to connect to database: {database.debug_string}'
                )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return

    def prefix_table(self, table: str) -> str:
        return self.database.prefix_table(table)

    def query(
                self,
                query: str,
                parameters: tuple = ()
            ) -> Generator[Dict[str, Any], None, None]:
        try:
            cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute(query, parameters)
            for result in cursor:
                yield result
            cursor.close()
        except pymysql.MySQLError:
            raise WordpressDatabaseException(
                    self.database,
                    'Failed to execute query'
                )

    def query_literal(
                self,
                query: str
            ) -> Generator[Dict[str, Any], None, None]:
        return self.query(
                query.replace('%', '%%')
            )

    def get_column_types(
                self,
                table: str,
                prefix: bool = False
            ) -> Dict[str, str]:
        if prefix:
            table = self.prefix_table(table)
        columns = {}
        for result in self.query(f'SHOW COLUMNS FROM {table}'):
            columns[result['Field'].lower()] = result['Type']
        return columns

    def set_variable(
                self,
                variable: str,
                value: str
            ) -> None:
        self.query('SET %s = %s', (variable, value))

    def set_collation(self, collation: str) -> None:
        self.set_variable('collation_connection', collation)


class WordpressDatabaseServer:

    def __init__(
                self,
                host: str = DEFAULT_HOST,
                port: int = DEFAULT_PORT,
                user: str = DEFAULT_USER,
                password: Optional[str] = None
            ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password


class WordpressDatabase:

    def __init__(
                self,
                name: str,
                server: WordpressDatabaseServer,
                prefix: str = DEFAULT_PREFIX,
                collation: str = DEFAULT_COLLATION
            ):
        self.name = name
        self.server = server
        self.prefix = prefix
        self.collation = collation
        self.debug_string = self._build_debug_string()

    def connect(self) -> WordpressDatabaseConnection:
        return WordpressDatabaseConnection(self)

    def _build_debug_string(self) -> str:
        return (
                f'{self.server.user}@{self.server.host}:'
                f'{self.server.port}/{self.name}'
            )

    def prefix_table(self, table: str) -> str:
        return self.prefix + table
