from wordfence.wordpress.database import WordpressDatabase, \
    WordpressDatabaseServer, DEFAULT_PORT, DEFAULT_COLLATION
from wordfence.wordpress.site import WordpressLocator, \
    WordpressSite
from wordfence.wordpress.exceptions import WordpressException
from wordfence.intel.database_rules import DatabaseRuleSet, load_database_rules
from wordfence.databasescanning.scanner import DatabaseScanner
from wordfence.util.validation import ListValidator, DictionaryValidator, \
    OptionalValueValidator
from getpass import getpass
from typing import Optional, List, Generator
import os
import json

from ...logging import log
from ..subcommands import Subcommand
from ..io import IoManager
from ..exceptions import ConfigurationException


class DbScanSubcommand(Subcommand):

    def _resolve_password(self) -> Optional[str]:
        if self.config.password is not None:
            log.warning(
                    'Providing passwords via command line parameters is '
                    'insecure as they can be exposed to other users'
                )
            return self.config.password
        elif self.config.prompt_for_password:
            return getpass()
        return os.environ.get(self.config.password_env)

    def _get_base_database(self) -> Optional[WordpressDatabase]:
        name = self.config.database_name
        if name is None:
            return None
        server = WordpressDatabaseServer(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self._resolve_password()
            )
        return WordpressDatabase(
                name=name,
                server=server,
                collation=self.config.collation
            )

    def _get_search_paths(
                self,
                include_current: bool = False
            ) -> Generator[bytes, None, None]:
        io_manager = IoManager(
                self.config.read_stdin,
                self.config.path_separator,
                binary=True
            )
        if len(self.config.trailing_arguments):
            yield from self.config.trailing_arguments
        elif include_current and not io_manager.should_read_stdin():
            yield os.fsencode(os.getcwd())
        if io_manager.should_read_stdin():
            for path in io_manager.get_input_reader().read_all_entries():
                yield path

    def _locate_site_databases(
                self
            ) -> Generator[WordpressDatabase, None, None]:
        for path in self._get_search_paths(include_current=True):
            locator = WordpressLocator(
                    path=path,
                    allow_nested=self.config.allow_nested,
                    allow_io_errors=self.config.allow_io_errors
                )
            for core_path in locator.locate_core_paths():
                site = WordpressSite(core_path)
                log.debug(
                        'Located WordPress site at ' + os.fsdecode(core_path)
                    )
                try:
                    database = site.get_database()
                    yield database
                except WordpressException:
                    if self.config.allow_io_errors:
                        log.warning(
                                'Failed to extract database credentials '
                                'for site at ' + os.fsdecode(core_path)
                            )
                    else:
                        raise

    def _get_json_validator(self) -> ListValidator:
        return ListValidator(
                DictionaryValidator({
                        'name': str,
                        'user': str,
                        'password': str,
                        'host': str,
                        'port': OptionalValueValidator(int),
                        'collation': OptionalValueValidator(str)
                    }, optional_keys={'port'})
            )

    def _parse_configured_databases(
                self
            ) -> Generator[WordpressDatabase, None, None]:
        validator = self._get_json_validator()
        for path in self._get_search_paths():
            with open(path, 'rb') as file:
                configList = json.load(file)
                validator.validate(configList)
                for config in configList:
                    try:
                        port = config['port']
                    except KeyError:
                        port = DEFAULT_PORT
                    try:
                        collation = config['collation']
                    except KeyError:
                        collation = DEFAULT_COLLATION
                    yield WordpressDatabase(
                            name=config['name'],
                            server=WordpressDatabaseServer(
                                    host=config['host'],
                                    port=port,
                                    user=config['user'],
                                    password=config['password']
                                ),
                            collation=collation
                        )

    def _get_databases(self) -> List[WordpressDatabase]:
        databases = []
        base = self._get_base_database()
        if base is not None:
            databases.append(base)
        generator = self._locate_site_databases() if \
            self.config.locate_sites else \
            self._parse_configured_databases()
        for database in generator:
            databases.append(database)
        return databases

    def _load_rules(self) -> DatabaseRuleSet:
        rule_set = DatabaseRuleSet()
        for rules_file in self.config.rules_file:
            load_database_rules(rules_file, rule_set)
        return rule_set

    def invoke(self) -> int:
        rule_set = self._load_rules()
        print(repr(vars((rule_set.rules[1]))))
        scanner = DatabaseScanner(rule_set)
        for database in self._get_databases():
            scanner.scan(database)
        if self.context.requires_input(self.config.require_database) \
                and scanner.scan_count == 0:
            raise ConfigurationException(
                    'At least one database to scan must be specified'
                )
        return 0


factory = DbScanSubcommand
