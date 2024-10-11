import os
import os.path
from dataclasses import dataclass, field
from typing import Optional, List, Generator, Dict, Callable, Any

from ..php.parsing import parse_php_file, PhpException, PhpState, \
    PhpEvaluationOptions
from ..logging import log
from ..util.io import is_symlink_loop, PathSet, resolve_path, \
    resolve_parent_path
from .exceptions import WordpressException, ExtensionException
from .plugin import Plugin, PluginLoader
from .theme import Theme, ThemeLoader
from .database import WordpressDatabase, WordpressDatabaseServer, \
    DEFAULT_PORT, DEFAULT_COLLATION

WP_BLOG_HEADER_NAME = b'wp-blog-header.php'
WP_CONFIG_NAME = b'wp-config.php'

EXPECTED_CORE_FILES = {
        WP_BLOG_HEADER_NAME,
        b'wp-load.php'
    }
EXPECTED_CORE_DIRECTORIES = {
        b'wp-admin',
        b'wp-includes'
    }

EVALUATION_OPTIONS = PhpEvaluationOptions(
        allow_includes=False
    )

ALTERNATE_RELATIVE_CONTENT_PATHS = [
        b'../app'
    ]

DATABASE_CONFIG_CONSTANTS = {
        b'DB_NAME': 'name',
        b'DB_USER': 'user',
        b'DB_PASSWORD': 'password',
        b'DB_HOST': 'host',
        b'DB_COLLATE': 'collation'
    }


@dataclass
class WordpressStructureOptions:
    relative_content_paths: List[str] = field(default_factory=list)
    relative_plugins_paths: List[str] = field(default_factory=list)
    relative_mu_plugins_paths: List[str] = field(default_factory=list)


class PathResolver:

    def __init__(self, path: bytes):
        self.path = path

    def _resolve_path(self, path: bytes, base: bytes) -> bytes:
        return os.path.join(base, path.lstrip(b'/'))

    def resolve_path(self, path: bytes) -> bytes:
        return self._resolve_path(path, self.path)


class WordpressLocator(PathResolver):

    def __init__(
                self,
                path: bytes,
                allow_nested: bool = True,
                allow_io_errors: bool = False
            ):
        super().__init__(path)
        self.allow_nested = allow_nested
        self.allow_io_errors = allow_io_errors

    def _is_core_directory(self, path: bytes, quiet: bool = False) -> bool:
        missing_files = EXPECTED_CORE_FILES.copy()
        missing_directories = EXPECTED_CORE_DIRECTORIES.copy()
        try:
            for file in os.scandir(path):
                try:
                    if file.is_file():
                        if file.name in missing_files:
                            missing_files.remove(file.name)
                    elif file.is_dir():
                        if file.name in missing_directories:
                            missing_directories.remove(file.name)
                except OSError as error:
                    if self.allow_io_errors:
                        log.warning(
                                'Unable to determine if ' +
                                os.fsdecode(file.path) + ' is an '
                                'expected WordPress file as its type could '
                                f'not be determined: {error}'
                            )
                        continue
                    else:
                        raise
            if len(missing_files) > 0 or len(missing_directories) > 0:
                return False
            return True
        except OSError as error:
            if self.allow_io_errors:
                log.warning(
                        'Unable to scan directory at ' + os.fsdecode(path)
                        + f': {error}'
                    )
                return False
            else:
                raise WordpressException(
                        'Unable to scan directory at ' + os.fsdecode(path)
                    ) from error
        return False

    def _extract_core_path_from_index(self) -> Optional[str]:
        try:
            context = parse_php_file(self.resolve_path(b'index.php'))
            for include in context.get_includes():
                path = include.evaluate_path(context.state)
                basename = os.path.basename(path)
                if basename == WP_BLOG_HEADER_NAME:
                    return os.path.dirname(path)
        except PhpException:
            # If parsing fails, it's not a valid WordPress index file
            pass
        return None

    def _get_child_directories(
                self,
                path: bytes,
                processed: PathSet
            ) -> List[bytes]:
        directories = []
        for file in os.scandir(path):
            try:
                if file.is_dir():
                    if file.is_symlink() and \
                            is_symlink_loop(file.path, processed):
                        continue
                    directories.append(os.path.realpath(file.path))
            except OSError as error:
                if self.allow_io_errors:
                    log.warning(
                            'Ignoring child entry at '
                            + os.fsdecode(file.path) + ' as its type '
                            f'could not be determined: {error}'
                        )
                else:
                    raise WordpressException(
                            'Unable to determine type of file at '
                            + os.fsdecode(file.path)
                        )
        return directories

    def _search_for_core_directory(
                self,
                located: PathSet,
                processed: PathSet
            ) -> Generator[bytes, None, None]:
        paths = [self.path]
        while len(paths) > 0:
            directories = set()
            for path in paths:
                try:
                    directories.update(
                            self._get_child_directories(path, processed)
                        )
                except OSError as error:
                    message = (
                            'Unable to search child directory at '
                            + os.fsdecode(path) + ' due to IO error'
                        )
                    if self.allow_io_errors:
                        log.warning(message + f': {error}')
                    else:
                        raise WordpressException(message) from error
            paths = set()
            for directory in directories:
                processed.add(directory)
                if self._is_core_directory(directory):
                    if directory not in located:
                        yield directory
                        if self.allow_nested:
                            paths.add(directory)
                        located.add(directory)
                else:
                    paths.add(directory)

    def locate_core_paths(self) -> Generator[bytes, None, None]:
        located = PathSet()
        if self._is_core_directory(self.path):
            yield self.path
            if not self.allow_nested:
                return
            located.add(resolve_path(self.path))
        path = self._extract_core_path_from_index()
        if path is None:
            processed = PathSet()
            processed.add(self.path)
            yield from self._search_for_core_directory(located, processed)
        else:
            yield os.fsencode(path)

    def locate_parent_installation(self) -> Optional[bytes]:
        current = resolve_path(self.path)
        if not os.path.isdir(current):
            current = resolve_parent_path(current)
        while True:
            if self._is_core_directory(current):
                return current
            parent = resolve_parent_path(current)
            if parent == current:
                break
            current = parent
        return None


def locate_core_path(
            path: bytes,
            up: bool = False,
            allow_io_errors: bool = False
        ) -> bytes:
    locator = WordpressLocator(path, allow_io_errors=allow_io_errors)
    if up:
        core_path = locator.locate_parent_installation()
        if core_path is None:
            raise WordpressException(
                    'Unable to locate core files above '
                    + os.fsdecode(path)
                )
        return core_path
    else:
        for path in locator.locate_core_paths():
            return path
        raise WordpressException(
                'Unable to locate core files under '
                + os.fsdecode(path)
            )


class WordpressSite(PathResolver):

    def __init__(
                self,
                path: bytes,
                structure_options: Optional[WordpressStructureOptions] = None,
                core_path: bytes = None,
                is_child_path: bool = False,
                allow_io_errors: bool = False
            ):
        super().__init__(path)
        self.core_path = locate_core_path(path, is_child_path, allow_io_errors)
        self.structure_options = structure_options \
            if structure_options is not None else WordpressStructureOptions()
        self._version = None

    def resolve_core_path(self, path: bytes) -> bytes:
        return self._resolve_path(path, self.core_path)

    def resolve_content_path(self, path: bytes) -> bytes:
        return self._resolve_path(path, self.get_content_directory())

    def _determine_version(self) -> bytes:
        version_path = self.resolve_core_path(b'wp-includes/version.php')
        context = parse_php_file(version_path)
        try:
            state = context.evaluate(
                    options=EVALUATION_OPTIONS
                )
            version = state.get_variable_value(b'wp_version')
            if isinstance(version, bytes):
                return version
        except PhpException as exception:
            raise WordpressException(
                    'Unable to parse WordPress version file at '
                    + os.fsdecode(version_path)
                ) from exception
        raise WordpressException('Unable to determine WordPress version')

    def get_version(self) -> str:
        if self._version is None:
            self._version = self._determine_version()
        return self._version

    def _locate_config_file(self) -> str:
        paths = [
                self.resolve_core_path(b'wp-config.php'),
                os.path.join(os.path.dirname(self.core_path), b'wp-config.php')
            ]
        for path in paths:
            if os.path.isfile(path):
                return path
        return None

    def _parse_config_file(self) -> Optional[PhpState]:
        config_path = self._locate_config_file()
        try:
            if config_path is not None:
                context = parse_php_file(config_path)
                return context.evaluate(
                        options=EVALUATION_OPTIONS
                    )
        except PhpException as exception:
            # Ignore config files that cannot be parsed
            log.debug(
                    'Unable to parse WordPress config file at '
                    + os.fsdecode(config_path)
                    + f' : {exception}'
                )
        return None

    def _get_parsed_config_state(self) -> PhpState:
        if not hasattr(self, 'config_state'):
            self.config_state = self._parse_config_file()
        return self.config_state

    def _extract_string_from_config(
                self,
                constant: bytes,
                default: Optional[bytes],
                extractor: Callable[[PhpState], Any]
            ) -> bytes:
        try:
            state = self._get_parsed_config_state()
            if state is not None:
                value = extractor(state)
                if isinstance(value, bytes):
                    return value
        except PhpException as exception:
            # Just use the default if parsing errors occur
            log.warning(
                    f'Unable to extract constant {constant} from WordPress '
                    f'config: {exception}'
                )
        return default

    def _extract_string_from_config_constant(
                self,
                constant: bytes,
                default: Optional[bytes] = None
            ):
        def get_constant_value(state: PhpState):
            return state.get_constant_value(
                    name=constant,
                    default_to_name=False
                )
        return self._extract_string_from_config(
                constant,
                default,
                get_constant_value
            )

    def _extract_string_from_config_variable(
                self,
                variable: bytes,
                default: Optional[bytes] = None
            ):
        def get_variable_value(state: PhpState):
            return state.get_variable_value(variable)
        return self._extract_string_from_config(
                variable,
                default,
                get_variable_value
            )

    def get_config_constant(self, constant: bytes) -> bytes:
        return self._extract_string_from_config_constant(constant)

    def get_config_variable(self, variable: bytes) -> bytes:
        return self._extract_string_from_config_variable(variable)

    def _generate_possible_content_paths(self) -> Generator[str, None, None]:
        configured = self._extract_string_from_config_constant(
                'WP_CONTENT_DIR'
            )
        if configured is not None:
            yield configured
        for path in self.structure_options.relative_content_paths:
            yield self.resolve_core_path(path)
        for path in ALTERNATE_RELATIVE_CONTENT_PATHS:
            yield self.resolve_core_path(path)
        yield self.resolve_core_path(b'wp-content')

    def _locate_content_directory(self) -> str:
        for path in self._generate_possible_content_paths():
            log.debug('Checking potential content path: ' + os.fsdecode(path))
            possible_themes_path = self._resolve_path(b'themes', path)
            if os.path.isdir(path) and os.path.isdir(possible_themes_path):
                log.debug('Located content directory at ' + os.fsdecode(path))
                return path
        raise WordpressException(
                'Unable to locate content directory for site at '
                + os.fsdecode(self.path)
            )

    def get_content_directory(self) -> str:
        if not hasattr(self, 'content_path'):
            self.content_path = self._locate_content_directory()
        return self.content_path

    def get_configured_plugins_directory(self, mu: bool = False) -> str:
        return self._extract_string_from_config_constant(
                'WPMU_PLUGIN_DIR' if mu else 'WP_PLUGIN_DIR',
            )

    def _generate_possible_plugins_paths(
                self,
                mu: bool = False,
                allow_io_errors: bool = False
            ) -> Generator[str, None, None]:
        configured = self.get_configured_plugins_directory(mu)
        if configured is not None:
            yield configured
        relative_paths = self.structure_options.relative_mu_plugins_paths \
            if mu else self.structure_options.relative_plugins_paths
        for path in relative_paths:
            yield self.resolve_core_path(path)
        try:
            yield self.resolve_content_path(
                    b'mu-plugins' if mu else b'plugins'
                )
        except WordpressException:
            if not allow_io_errors:
                raise

    def get_plugins(
                self,
                mu: bool = False,
                allow_io_errors: bool = False
            ) -> List[Plugin]:
        log_plugins = 'must-use plugins' if mu else 'plugins'
        for path in self._generate_possible_plugins_paths(mu, allow_io_errors):
            log.debug(
                    f'Checking potential {log_plugins} path: '
                    + os.fsdecode(path)
                )
            loader = PluginLoader(path, allow_io_errors)
            try:
                plugins = loader.load_all()
                log.debug(
                        f'Located {log_plugins} directory at '
                        + os.fsdecode(path)
                    )
                return plugins
            except ExtensionException:
                # If extensions can't be loaded, the directory is not valid
                continue
        if mu:
            log.warning(
                    'No mu-plugins directory found for site at '
                    + os.fsdecode(self.path)
                )
            return []
        if allow_io_errors:
            return []
        raise WordpressException(
                f'Unable to locate {log_plugins} directory for site at '
                + os.fsdecode(self.path)
            )

    def get_all_plugins(self, allow_io_errors: bool = False) -> List[Plugin]:
        plugins = self.get_plugins(mu=True, allow_io_errors=allow_io_errors)
        plugins += self.get_plugins(mu=False, allow_io_errors=allow_io_errors)
        return plugins

    def get_theme_directory(self) -> str:
        return self.resolve_content_path(b'themes')

    def get_themes(self, allow_io_errors: bool = False) -> List[Theme]:
        try:
            directory = self.get_theme_directory()
        except WordpressException:
            if allow_io_errors:
                return []
            else:
                raise
        loader = ThemeLoader(directory, allow_io_errors)
        return loader.load_all()

    def _extract_database_config(self) -> Dict[str, str]:
        config = {}

        def add_config(key: str, value: Any):
            if value is None:
                raise WordpressException(
                        'Unable to extract database connection details from '
                        f'WordPress config (Key: {key}, Value: '
                        + repr(value) + ')'
                    )
            config[key] = value.decode('latin1')

        for constant, attribute in DATABASE_CONFIG_CONSTANTS.items():
            add_config(
                    key=attribute,
                    value=self.get_config_constant(constant)
                )
        add_config(
                key='prefix',
                value=self.get_config_variable(b'table_prefix')
            )
        return config

    def get_database(self) -> WordpressDatabase:
        config = self._extract_database_config()
        host_components = config['host'].split(':', 1)
        host = host_components[0]
        try:
            port = int(host_components[1])
        except IndexError:
            port = DEFAULT_PORT
        try:
            collation = config['collation']
        except KeyError:
            collation = DEFAULT_COLLATION
        server = WordpressDatabaseServer(
                host=host,
                port=port,
                user=config['user'],
                password=config['password']
            )
        return WordpressDatabase(
                name=config['name'],
                server=server,
                prefix=config['prefix'],
                collation=collation
            )
