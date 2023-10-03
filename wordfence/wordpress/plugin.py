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

    def _process_entry(self, entry: os.DirEntry) -> Optional[Plugin]:
        path = Path(entry.path)
        if entry.is_file():
            slug = path.stem
            return self.load(slug, path)
        elif entry.is_dir():
            slug = entry.name
            path = path / f'{slug}.php'
            if path.is_file():
                return self.load(slug, path)
        return None
