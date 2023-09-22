import os
import os.path
from typing import Optional, List, Dict

from ..php.parsing import parse_php_file, PhpException
from .exceptions import WordpressException
from .plugin import Plugin
from .theme import Theme

WP_BLOG_HEADER_NAME = 'wp-blog-header.php'

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
        except PhpException as exception:
            # If parsing fails, it's not a valid WordPress index file
            raise exception
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

    def get_plugin_directory(self) -> str:
        # TODO Parse WP config to determine plugin path
        return self.resolve_core_path('wp-content/plugins')

    def _read_plugin_header(path: str) -> Dict[str, str]:
        header = {}
        # TODO:
        return header

    def get_plugins(self) -> List[Plugin]:
        plugins = []
        directory = self.get_plugin_directory()
        try:
            for file in os.scandir(directory):
                if file.is_file():
                    header = self._read_plugin_header(file.path)
                elif file.is_dir():
                    # TODO
                    pass
                pass
        except OSError as error:
            raise WordpressException(
                    f'Unable to scan plugins directory at {directory}'
                ) from error
        return plugins

    def get_themes(self) -> List[Theme]:
        return []
