import mysql.connector
from typing import Optional, Generator

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
            self.connection = mysql.connector.connect(
                    host=database.server.host,
                    port=database.server.port,
                    user=database.server.user,
                    password=database.server.password,
                    database=database.name,
                    collation=database.collation
                )
        except mysql.connector.Error:
            raise WordpressDatabaseException(
                    database,
                    f'Failed to connect to database: {database.debug_string}'
                )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return

    def query(
                self,
                query: str,
                parameters: tuple = ()
            ) -> Generator[tuple, None, None]:
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, parameters)
            for result in cursor:
                yield result
            cursor.close()
        except mysql.connector.Error:
            raise WordpressDatabaseException(
                    self.database,
                    'Failed to execute query'
                )


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
