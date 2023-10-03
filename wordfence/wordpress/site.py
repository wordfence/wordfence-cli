import os
import os.path
from typing import Optional, List

from ..php.parsing import parse_php_file, PhpException, PhpState
from .exceptions import WordpressException
from .plugin import Plugin, PluginLoader
from .theme import Theme, ThemeLoader

WP_BLOG_HEADER_NAME = 'wp-blog-header.php'
WP_CONFIG_NAME = 'wp-config.php'

EXPECTED_CORE_FILES = {
        WP_BLOG_HEADER_NAME,
        'wp-load.php'
    }

EXPECTED_CORE_DIRECTORIES = {
        'wp-admin',
        'wp-includes'
    }


class WordpressSite:

    def __init__(self, path: str):
        self.path = path
        self.core_path = self._locate_core()
        # self.config_state = self._parse_config_file()
        # print(vars(self.config_state))
        # print(repr(self.config_state.global_scope.variables))
        # print(repr(self.config_state.constants))
        # raise Exception('Test')

    def _is_core_directory(self, path: str) -> bool:
        missing_files = EXPECTED_CORE_FILES.copy()
        missing_directories = EXPECTED_CORE_DIRECTORIES.copy()
        try:
            for file in os.scandir(path):
                if file.is_file():
                    if file.name in missing_files:
                        missing_files.remove(file.name)
                elif file.is_dir():
                    if file.name in missing_directories:
                        missing_directories.remove(file.name)
            if len(missing_files) > 0 or len(missing_directories) > 0:
                return False
            return True
        except OSError as error:
            raise WordpressException(
                    f'Unable to scan directory at {path}'
                ) from error
        return False

    def _extract_core_path_from_index(self) -> Optional[str]:
        try:
            context = parse_php_file(self.resolve_path('index.php'))
            for include in context.get_includes():
                path = include.evaluate_path(context.state)
                basename = os.path.basename(path)
                if basename == WP_BLOG_HEADER_NAME:
                    return os.path.dirname(path)
        except PhpException:
            # If parsing fails, it's not a valid WordPress index file
            pass
        return None

    def _get_child_directories(self, path: str) -> List[str]:
        directories = []
        for file in os.scandir(path):
            if file.is_dir():
                directories.append(file.path)
        return directories

    def _search_for_core_directory(self) -> Optional[str]:
        paths = [self.path]
        while len(paths) > 0:
            directories = []
            for path in paths:
                try:
                    directories.extend(self._get_child_directories(path))
                except OSError as error:
                    raise WordpressException(
                            f'Unable to search child directory at {path}'
                        ) from error
            for directory in directories:
                if self._is_core_directory(directory):
                    return directory
            paths = directories
        return None

    def _locate_core(self) -> str:
        if self._is_core_directory(self.path):
            return self.path
        path = self._extract_core_path_from_index()
        if path is None:
            path = self._search_for_core_directory()
        if path is not None:
            return path
        raise WordpressException(
                f'Unable to locate WordPress core files under {self.path}'
            )

    def _resolve_path(self, path: str, base: str) -> str:
        return os.path.join(base, path.lstrip('/'))

    def resolve_path(self, path: str) -> str:
        return self._resolve_path(path, self.path)

    def resolve_core_path(self, path: str) -> str:
        return self._resolve_path(path, self.core_path)

    def resolve_content_path(self, path: str) -> str:
        return self._resolve_path(path, self.get_content_directory())

    def get_version(self) -> str:
        version_path = self.resolve_core_path('wp-includes/version.php')
        context = parse_php_file(version_path)
        try:
            version = context.evaluate_variable('wp_version')
            if isinstance(version, str):
                return version
        except PhpException as exception:
            raise WordpressException(
                    f'Unable to parse WordPress version file at {version_path}'
                ) from exception
        raise WordpressException('Unable to determine WordPress version')

    def _locate_config_file(self) -> str:
        paths = [
                self.resolve_core_path('wp-config.php'),
                os.path.join(os.path.dirname(self.core_path), 'wp-config.php')
            ]
        for path in paths:
            if os.path.isfile(path):
                return path
        return None

    def _parse_config_file(self) -> PhpState:
        config_path = self._locate_config_file()
        try:
            if config_path is not None:
                print(f"Parsing config at {config_path}...")
                context = parse_php_file(config_path)
                return context.evaluate()
        except PhpException:
            raise  # TODO: Remove this
            # Ignore config files that cannot be parsed
            pass
        return PhpState()

    def _extract_string_from_config(self, constant: str, default: str) -> str:
        try:
            path = self.config_context.evaluate_constant(constant)
            # print(repr(path))
            # raise Exception('Exit')
            if isinstance(path, str):
                return path
        except PhpException:
            raise  # TODO: Remove this
            # Just use the default if parsing errors occur
            pass
        return default

    def _locate_content_directory(self) -> str:
        return self.resolve_core_path('wp-content')
        # return self._extract_string_from_config(
        #         'WP_CONTENT_DIR',
        #         self.resolve_core_path('wp-content')
        #     )

    def get_content_directory(self) -> str:
        if not hasattr(self, 'content_path'):
            self.content_path = self._locate_content_directory()
        return self.content_path

    def get_plugin_directory(self) -> str:
        return self.resolve_content_path('plugins')
        # return self._extract_string_from_config(
        #         'WP_PLUGIN_DIR',
        #         self.resolve_content_path('plugins')
        #     )

    def get_plugins(self) -> List[Plugin]:
        loader = PluginLoader(self.get_plugin_directory())
        return loader.load_all()

    def get_theme_directory(self) -> str:
        return self.resolve_content_path('themes')

    def get_themes(self) -> List[Theme]:
        loader = ThemeLoader(self.get_theme_directory())
        return loader.load_all()
