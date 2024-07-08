import os
from typing import Optional, Dict

from ..util.io import PathProperties
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

    def __init__(self, directory: str, allow_io_errors: bool = False):
        super().__init__(
                'plugin',
                directory=directory,
                header_fields=PLUGIN_HEADER_FIELDS,
                allow_io_errors=allow_io_errors
            )

    def _initialize_extension(
                self,
                slug: str,
                version: Optional[str],
                header: Dict[str, str],
                path: bytes
            ):
        return Plugin(
                slug=slug,
                version=version,
                header=header,
                path=path
            )

    def _has_php_extension(self, properties: PathProperties) -> bool:
        return properties.extension == b'.php'

    def _process_entry(self, entry: os.DirEntry) -> Optional[Plugin]:
        # Ignore dot files
        if entry.name.find(b'.') == 0:
            return None
        if entry.is_file():
            path_properties = PathProperties(entry.path)
            if self._has_php_extension(path_properties):
                return self.load(
                        os.fsdecode(path_properties.stem),
                        entry.path,
                    )
        elif entry.is_dir():
            slug = os.fsdecode(entry.name)
            for child in os.scandir(entry.path):
                if child.is_file():
                    child_path = os.path.join(entry.path, child.name)
                    if self._has_php_extension(PathProperties(child_path)):
                        plugin = self.load(
                                slug,
                                child_path,
                                base_path=entry.path
                            )
                        if plugin is not None:
                            return plugin
        return None
