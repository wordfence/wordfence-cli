import os
from typing import Optional, Dict

from .extension import Extension, ExtensionLoader


THEME_HEADER_FIELDS = {
        'Name': 'Theme Name',
        'ThemeURI': 'Theme URI',
        'Description': 'Description',
        'Author': 'Author',
        'AuthorURI': 'Author URI',
        'Version': 'Version',
        'Template': 'Template',
        'Status': 'Status',
        'Tags': 'Tags',
        'TextDomain': 'Text Domain',
        'DomainPath': 'Domain Path',
        'RequiresWP': 'Requires at least',
        'RequiresPHP': 'Requires PHP'
    }


class Theme(Extension):
    pass


class ThemeLoader(ExtensionLoader):

    def __init__(self, directory: str, allow_io_errors: bool = False):
        super().__init__(
                'theme',
                directory=directory,
                header_fields=THEME_HEADER_FIELDS,
                allow_io_errors=allow_io_errors
            )

    def _initialize_extension(
                self,
                slug: str,
                version: Optional[str],
                header: Dict[str, str],
                path: bytes
            ):
        return Theme(
                slug=slug,
                version=version,
                header=header,
                path=path
            )

    def _process_entry(self, entry: os.DirEntry) -> Optional[Theme]:
        if not entry.is_dir():
            return None
        path = os.path.join(entry.path, b'style.css')
        if not os.path.isfile(path):
            return None
        slug = os.fsdecode(entry.name)
        return self.load(slug, path, base_path=entry.path)
