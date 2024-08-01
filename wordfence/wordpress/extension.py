import re
import os
from typing import Optional, Dict, List

from ..logging import log
from ..util.io import SYMLINK_IO_ERRORS
from ..util.encoding import str_to_bytes
from .exceptions import ExtensionException


HEADER_READ_SIZE = 8 * 1024
HEADER_CLEANUP_PATTERN = re.compile(r'\s*(?:\*\/|\?>).*')
CARRIAGE_RETURN_PATTERN = re.compile('\r')


class Extension:

    def __init__(
                self,
                slug: str,
                version: Optional[bytes],
                header: Dict[str, str],
                path: bytes
            ):
        self.slug = slug
        self.version = version
        self.header = header
        self.path = path

    def get_name(self) -> str:
        try:
            return self.header['Name']
        except KeyError:
            return self.slug

    def __str__(self) -> str:
        return f'{self.slug}({self.version})'


class ExtensionLoader:

    def __init__(
                self,
                extension_type: str,
                directory: str,
                header_fields: Dict[str, str],
                allow_io_errors: bool = False,
            ):
        self.extension_type = extension_type
        self.directory = directory
        self.header_fields = header_fields
        self.allow_io_errors = allow_io_errors

    def _clean_up_header_value(self, value: str) -> str:
        return HEADER_CLEANUP_PATTERN.sub('', value).strip()

    def _read_header(self, path: bytes) -> str:
        try:
            with open(path, 'r', errors='replace') as stream:
                data = stream.read(HEADER_READ_SIZE)
                return data
        except OSError as error:
            raise ExtensionException(
                    f'Unable to read {self.extension_type} header from '
                    + os.fsdecode(path)
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

    def load(
                self,
                slug: str,
                path: bytes,
                base_path: Optional[bytes] = None
            ) -> Optional[Extension]:
        header_data = self._read_header(path)
        header = self._parse_header(header_data)
        if 'Name' not in header:
            return None
        try:
            version = header['Version']
            if isinstance(version, str):
                version = str_to_bytes(version)
        except KeyError:
            version = None
        if base_path is None:
            base_path = path
        return self._initialize_extension(slug, version, header, base_path)

    def _initialize_extension(
                self,
                slug: str,
                version: Optional[str],
                header: Dict[str, str],
                path: bytes
            ):
        return Extension(
                slug=slug,
                version=version,
                header=header,
                path=path
            )

    def _process_entry(entry: os.DirEntry) -> Optional[Extension]:
        return None

    def load_all(self) -> List[Extension]:
        extensions = []
        try:
            for entry in os.scandir(self.directory):
                try:
                    extension = self._process_entry(entry)
                    if extension is not None:
                        extensions.append(extension)
                except OSError as error:
                    if error.errno in SYMLINK_IO_ERRORS:
                        continue
                    if self.allow_io_errors:
                        log.warning(
                                f'Unable to load {self.extension_type} from '
                                + os.fsdecode(entry.path) + f': {error}'
                            )
                    else:
                        raise
        except OSError as error:
            if error.errno not in SYMLINK_IO_ERRORS:
                message = (
                        f'Unable to scan {self.extension_type} directory at '
                        + os.fsdecode(self.directory)
                    )
                if self.allow_io_errors:
                    log.warning(message)
                else:
                    raise ExtensionException(message) from error
        return extensions
