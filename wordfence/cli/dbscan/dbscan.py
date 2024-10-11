from wordfence.wordpress.database import WordpressDatabase, \
    WordpressDatabaseServer, DEFAULT_PORT, DEFAULT_COLLATION, DEFAULT_PREFIX
from wordfence.wordpress.site import WordpressLocator, \
    WordpressSite
from wordfence.wordpress.exceptions import WordpressException
from wordfence.intel.database_rules import DatabaseRuleSet, load_database_rules
from wordfence.databasescanning.scanner import DatabaseScanner
from wordfence.util.validation import ListValidator, DictionaryValidator, \
    OptionalValueValidator
from wordfence.util import caching
from getpass import getpass
from typing import Optional, List, Generator
import os
import json

from ...logging import log
from ..subcommands import Subcommand
from ..io import IoManager
from ..exceptions import ConfigurationException
from ..config import not_set_token

from .reporting import DatabaseScanReportManager


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
                prefix=self.config.prefix,
                collation=self.config.collation
            )

    def _get_search_paths(
                self,
                io_manager: IoManager,
                include_current: bool = False
            ) -> Generator[bytes, None, None]:
        if len(self.config.trailing_arguments):
            yield from self.config.trailing_arguments
        elif include_current and not io_manager.should_read_stdin():
            yield os.fsencode(os.getcwd())
        if io_manager.should_read_stdin():
            for path in io_manager.get_input_reader().read_all_entries():
                yield path

    def _locate_site_databases(
                self,
                io_manager: IoManager
            ) -> Generator[WordpressDatabase, None, None]:
        for path in self._get_search_paths(io_manager, include_current=True):
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
                        'collation': OptionalValueValidator(str),
                        'prefix': OptionalValueValidator(str)
                    }, optional_keys={'port', 'collation'})
            )

    def _parse_configured_databases(
                self,
                io_manager: IoManager
            ) -> Generator[WordpressDatabase, None, None]:
        validator = self._get_json_validator()
        for path in self._get_search_paths(io_manager):
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
                    try:
                        prefix = config['prefix']
                    except KeyError:
                        prefix = DEFAULT_PREFIX
                    yield WordpressDatabase(
                            name=config['name'],
                            server=WordpressDatabaseServer(
                                    host=config['host'],
                                    port=port,
                                    user=config['user'],
                                    password=config['password']
                                ),
                            prefix=prefix,
                            collation=collation
                        )

    def _get_databases(
                self,
                io_manager: IoManager
            ) -> List[WordpressDatabase]:
        databases = []
        base = self._get_base_database()
        if base is not None:
            databases.append(base)
        generator = self._locate_site_databases(io_manager) if \
            self.config.locate_sites else \
            self._parse_configured_databases(io_manager)
        for database in generator:
            databases.append(database)
        return databases

    def _load_remote_rules(self) -> DatabaseRuleSet:

        def fetch_rules() -> DatabaseRuleSet:
            client = self.context.get_noc1_client()
            return client.get_database_rules()

        cacheable = caching.Cacheable(
                'database_rules',
                fetch_rules,
                caching.DURATION_ONE_DAY
            )

        return cacheable.get(self.cache)

    def _filter_rules(self, rule_set: DatabaseRuleSet) -> None:
        included = None
        if self.config.include_rules:
            included = set(self.config.include_rules)
        excluded = None
        if self.config.exclude_rules:
            excluded = set(self.config.exclude_rules)
        rule_set.filter_rules(included, excluded)

    def _load_rules(self) -> DatabaseRuleSet:
        rule_set = self._load_remote_rules() \
            if self.config.use_remote_rules \
            else DatabaseRuleSet()
        if self.config.rules_file is not not_set_token:
            for rules_file in self.config.rules_file:
                load_database_rules(rules_file, rule_set)
        self._filter_rules(rule_set)
        return rule_set

    def invoke(self) -> int:
        report_manager = DatabaseScanReportManager(self.context)
        io_manager = report_manager.get_io_manager()
        rule_set = self._load_rules()
        scanner = DatabaseScanner(rule_set)
        with report_manager.open_output_file() as output_file:
            report = report_manager.initialize_report(output_file)
            for database in self._get_databases(io_manager):
                for result in scanner.scan(database):
                    report.add_result(result)
            report.database_count = scanner.scan_count
            report.complete()
        if self.context.requires_input(self.config.require_database) \
                and scanner.scan_count == 0:
            raise ConfigurationException(
                    'At least one database to scan must be specified'
                )
        elapsed_time = round(scanner.get_elapsed_time())
        log.info(
                f'Found {report.result_count} result(s) after scanning '
                f'{scanner.scan_count} database(s) over {elapsed_time} '
                'second(s)'
            )
        return 0


factory = DbScanSubcommand
