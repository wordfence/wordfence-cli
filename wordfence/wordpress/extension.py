import re
import os
from typing import Optional, Dict, List
from pathlib import Path

from .exceptions import ExtensionException


HEADER_READ_SIZE = 8 * 1024
HEADER_CLEANUP_PATTERN = re.compile(r'\s*(?:\*\/|\?>).*')
CARRIAGE_RETURN_PATTERN = re.compile('\r')


class Extension:

    def __init__(
                self,
                slug: str,
                version: Optional[str],
                header: Dict[str, str]
            ):
        self.slug = slug
        self.version = version
        self.header = header


class ExtensionLoader:

    def __init__(
                self,
                directory: str,
                header_fields: Dict[str, str]
            ):
        self.directory = directory
        self.header_fields = header_fields

    def _clean_up_header_value(self, value: str) -> str:
        return HEADER_CLEANUP_PATTERN.sub('', value).strip()

    def _read_header(self, path: str) -> str:
        try:
            with open(path, 'r', errors='replace') as stream:
                data = stream.read(HEADER_READ_SIZE)
                return data
        except OSError as error:
            raise ExtensionException(
                    f'Unable to read extension header from {path}'
                ) from error

    def _parse_header(
                self,
                data: str,
            ) -> Dict[str, str]:
        data = CARRIAGE_RETURN_PATTERN.sub('\n', data)
        values = {}
        for field, pattern in self.header_fields.items():
            match = re.search(
                    '^[ \t\\/*#@]*' + re.escape(pattern) + r':(.*)$',
                    data,
                    re.MULTILINE | re.IGNORECASE
                )
            if match is not None:
                values[field] = self._clean_up_header_value(match.group(1))
        return values

    def load(self, slug: str, path: Path) -> Optional[Extension]:
        header_data = self._read_header(str(path))
        header = self._parse_header(header_data)
        if 'Name' not in header:
            return None
        try:
            version = header['Version']
        except KeyError:
            version = None
        return self._initialize_extension(slug, version, header)

    def _initialize_extension(
                self,
                slug: str,
                version: Optional[str],
                header: Dict[str, str]
            ):
        return Extension(
                slug=slug,
                version=version,
                header=header
            )

    def _process_entry(entry: os.DirEntry) -> Optional[Extension]:
        return None

    def load_all(self) -> List[Extension]:
        extensions = []
        try:
            for entry in os.scandir(self.directory):
                extension = self._process_entry(entry)
                if extension is not None:
                    extensions.append(extension)
        except OSError as error:
            raise ExtensionException(
                    f'Unable to scan extension directory at {self.directory}'
                ) from error
        return extensions
