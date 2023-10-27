import os
from typing import Optional, Dict
from pathlib import Path

from .extension import Extension, ExtensionLoader


PLUGIN_HEADER_FIELDS = {
        'Name': 'Plugin Name',
        'PluginURI': 'Plugin URI',
        'Version': 'Version',
        'Description': 'Description',
        'Author': 'Author',
        'AuthorURI': 'Author URI',
        'TextDomain': 'Test Domain',
        'DomainPath': 'Domain Path',
        'Network': 'Network',
        'RequiresWP': 'Requires at least',
        'RequiresPHP': 'Requires PHP',
        '_sitewide': 'Site Wide Only'
    }


class Plugin(Extension):
    pass


class PluginLoader(ExtensionLoader):

    def __init__(self, directory: str):
        super().__init__(
                directory=directory,
                header_fields=PLUGIN_HEADER_FIELDS
            )

    def _initialize_extension(
                self,
                slug: str,
                version: Optional[str],
                header: Dict[str, str]
            ):
        return Plugin(
                slug=slug,
                version=version,
                header=header
            )

    def _has_php_extension(self, path: Path) -> bool:
        return path.suffix == '.php'

    def _process_entry(self, entry: os.DirEntry) -> Optional[Plugin]:
        if entry.name.find('.') == 0:
            return None
        path = Path(entry.path)
        if entry.is_file():
            slug = path.stem
            if self._has_php_extension(path):
                return self.load(slug, path)
        elif entry.is_dir():
            slug = entry.name
            for child in os.scandir(entry.path):
                if child.is_file():
                    child_path = path / child.name
                    if self._has_php_extension(child_path):
                        plugin = self.load(slug, child_path)
                        if plugin is not None:
                            return plugin
        return None
