import os
from typing import Optional, Dict
from pathlib import Path

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

    def __init__(self, directory: str):
        super().__init__(
                directory=directory,
                header_fields=THEME_HEADER_FIELDS
            )

    def _initialize_extension(
                self,
                slug: str,
                version: Optional[str],
                header: Dict[str, str]
            ):
        return Theme(
                slug=slug,
                version=version,
                header=header
            )

    def _process_entry(self, entry: os.DirEntry) -> Optional[Theme]:
        if not entry.is_dir():
            return None
        base = Path(entry.path)
        path = base / 'style.css'
        if not path.is_file():
            return None
        slug = base.name
        return self.load(slug, path)
