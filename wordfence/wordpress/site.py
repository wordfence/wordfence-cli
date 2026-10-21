import os
import os.path
import pwd
from dataclasses import dataclass, field
from typing import Optional, List, Generator

from ..php.parsing import parse_php_file, PhpException, PhpState, \
    PhpEvaluationOptions
from ..logging import log
from ..util.io import get_site_paths, PRODUCTION_PATH, STAGING_PATH
from .exceptions import WordpressException, ExtensionException
from .plugin import Plugin, PluginLoader
from .theme import Theme, ThemeLoader

WP_BLOG_HEADER_NAME = 'wp-blog-header.php'
WP_CONFIG_NAME = 'wp-config.php'

EXPECTED_CORE_FILES = {
        WP_BLOG_HEADER_NAME
    }
EXPECTED_CORE_DIRECTORIES = {
        PRODUCTION_PATH,
        STAGING_PATH
    }

EVALUATION_OPTIONS = PhpEvaluationOptions(
        allow_includes=False
    )


@dataclass
class WordpressStructureOptions:
    relative_content_paths: List[str] = field(default_factory=list)
    relative_plugins_paths: List[str] = field(default_factory=list)
    relative_mu_plugins_paths: List[str] = field(default_factory=list)
    include_staging: bool = False

    def get_alternate_content_paths(self) -> List[str]:
        return get_site_paths(self.include_staging)


class WordpressSite:

    def __init__(
                self,
                path: str,
                structure_options: Optional[WordpressStructureOptions] = None,
                include_staging: bool = False,
            ):
        self.path = path
        self.core_path = ''
        if structure_options is not None:
            self.structure_options = structure_options
        else:
            self.structure_options = WordpressStructureOptions(
                    include_staging=include_staging
                )
            for site_path in \
                    self.structure_options.get_alternate_content_paths():
                site_path = os.path.join(path, site_path)
                if os.path.isdir(site_path):
                    self.structure_options.relative_content_paths.append(
                            site_path)

    def _is_core_directory(self, path: str) -> bool:
        return True

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
        try:
            for file in os.scandir(path):
                uid = file.stat().st_uid
                owner = pwd.getpwuid(uid).pw_name
                if file.is_dir() and owner not in ('root', 'nobody'):
                    directories.append(file.path)
        except OSError as error:
            raise WordpressException(
                    f'Unable to search child directory at {path}'
                ) from error
        return directories

    def _search_for_core_directory(self) -> Optional[str]:
        return self.path

    def _locate_core(self) -> str:
        return self.path

    def _resolve_path(self, path: str, base: str) -> str:
        return os.path.join(base, path.lstrip('/'))

    def resolve_core_path(self, path: str) -> str:
        return os.path.normpath(os.path.join(self.path, path))

    def resolve_content_path(self, path: str) -> str:
        return self._resolve_path(path, self.get_content_directory())

    def get_version(self) -> str:
        # Always return 'Flywheel', ignoring the version check
        return 'Flywheel'

    def _locate_config_file(self) -> str:
        # Skip checking wp-config.php
        return None

    def _parse_config_file(self) -> Optional[PhpState]:
        # Skip parsing wp-config.php
        return None

    def _get_parsed_config_state(self) -> PhpState:
        # Skip getting parsed config state
        return None

    def _extract_string_from_config(
                self,
                constant: str,
                default: Optional[str] = None
            ) -> str:
        # Skip extracting strings from config
        return default

    def _generate_possible_content_paths(self) -> Generator[str, None, None]:
        configured = self._extract_string_from_config(
            'WP_CONTENT_DIR'
        )
        if configured is not None:
            yield configured
        for path in self.structure_options.relative_content_paths:
            yield self.resolve_core_path(os.path.join(path, 'wp-content'))
        for path in self.structure_options.get_alternate_content_paths():
            yield self.resolve_core_path(os.path.join(path, 'wp-content'))

    def _locate_content_directory(self) -> List[str]:
        valid_directories = []
        for path in self._generate_possible_content_paths():
            log.debug(f'Checking potential content path: {path}')
            possible_themes_path = self._resolve_path('themes', path)
            if os.path.isdir(path) and os.path.isdir(possible_themes_path):
                log.debug(f'Located content directory at {path}')
                valid_directories.append(path)
        if not valid_directories:
            raise WordpressException(
                f'Unable to locate content directory for site at {self.path}'
            )
        return valid_directories

    def get_content_directory(self) -> str:
        if not hasattr(self, 'content_path'):
            self.content_path = self._locate_content_directory()
        return self.content_path

    def get_configured_plugins_directory(self, mu: bool = False) -> str:
        return self._extract_string_from_config(
                'WPMU_PLUGIN_DIR' if mu else 'WP_PLUGIN_DIR',
            )

    def _generate_possible_plugins_paths(
                self,
                mu: bool = False
            ) -> Generator[str, None, None]:
        configured = self.get_configured_plugins_directory(mu)
        if configured is not None:
            yield configured
        relative_paths = self.structure_options.relative_mu_plugins_paths \
            if mu else self.structure_options.relative_plugins_paths
        for path in relative_paths:
            yield self.resolve_core_path(path)
        for content_path in self.get_content_directory():
            yield self._resolve_path(
                'mu-plugins' if mu else 'plugins', content_path
            )

    def get_plugins(self, mu: bool = False) -> List[Plugin]:
        log_plugins = 'must-use plugins' if mu else 'plugins'
        plugins = []
        found_directory = False
        for path in self._generate_possible_plugins_paths(mu):
            log.debug(f'Checking potential {log_plugins} path: {path}')
            loader = PluginLoader(path)
            try:
                loaded_plugins = loader.load_all()
                if loaded_plugins is not None:
                    found_directory = True
                    plugins += loaded_plugins
                    log.debug(f'Located {log_plugins} directory at {path}')
            except ExtensionException:
                # If extensions can't be loaded, the directory is not valid
                continue
        if not found_directory and not mu:
            raise WordpressException(
                    f'Unable to locate {log_plugins} directory for site at '
                    f'{self.path}'
                )
        if mu and not plugins:
            log.debug(
                    f'No mu-plugins directory found for site at {self.path}'
                )
        return plugins

    def get_all_plugins(self) -> List[Plugin]:
        plugins = self.get_plugins(mu=True)
        plugins += self.get_plugins(mu=False)
        return plugins

    def get_theme_directory(self) -> str:
        return self.resolve_content_path('themes')

    def get_themes(self) -> List[Theme]:
        themes = []
        for content_path in self.get_content_directory():
            theme_directory = self._resolve_path('themes', content_path)
            loader = ThemeLoader(theme_directory)
            themes += loader.load_all()
        return themes
