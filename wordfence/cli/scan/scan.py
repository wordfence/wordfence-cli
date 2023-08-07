import sys
import signal
import os
from multiprocessing import parent_process

from wordfence import scanning, api
from wordfence.util import caching
from wordfence.util.io import StreamReader
from wordfence.intel.signatures import SignatureSet


class ScanCommand:

    CACHEABLE_TYPES = {
            'wordfence.intel.signatures.SignatureSet',
            'wordfence.intel.signatures.CommonString',
            'wordfence.intel.signatures.Signature'
        }

    def __init__(self, config):
        self.config = config
        self.cache = self._initialize_cache()
        self.license = None
        self.cacheable_signatures = None

    def _get_license(self) -> api.licensing.License:
        if self.license is None:
            if self.config.license is None:
                raise ValueError('A Wordfence CLI license is required')
            self.license = api.licensing.License(self.config.license)
        return self.license

    def _initialize_cache(self) -> caching.Cache:
        try:
            return caching.CacheDirectory(
                    self.config.cache_directory,
                    self.CACHEABLE_TYPES
                )
        except caching.CacheException:
            return caching.RuntimeCache()

    def filter_signatures(self, signatures: SignatureSet) -> None:
        if self.config.exclude_signatures is None:
            return
        for identifier in self.config.exclude_signatures:
            signatures.remove_signature(identifier)

    def _get_signatures(self) -> SignatureSet:
        if self.cacheable_signatures is None:
            def fetch_signatures() -> SignatureSet:
                noc1_client = api.noc1.Client(
                        self._get_license(),
                        base_url=self.config.noc1_url
                    )
                return noc1_client.get_malware_signatures()
            self.cacheable_signatures = caching.Cacheable(
                    'signatures',
                    fetch_signatures,
                    86400  # Cache signatures for 24 hours
                )
        signatures = self.cacheable_signatures.get(self.cache)
        self.filter_signatures(signatures)
        return signatures

    def _should_read_stdin(self) -> bool:
        if sys.stdin is None:
            return False
        if self.config.read_stdin is None:
            return not sys.stdin.isatty()
        else:
            return self.config.read_stdin

    def _get_file_list_separator(self) -> str:
        if isinstance(self.config.file_list_separator, bytes):
            return self.config.file_list_separator.decode('utf-8')
        return self.config.file_list_separator

    def execute(self) -> int:
        paths = set()
        for argument in self.config.trailing_arguments:
            paths.add(argument)
        options = scanning.scanner.Options(
                paths=paths,
                threads=int(self.config.threads),
                signatures=self._get_signatures(),
                chunk_size=self.config.chunk_size
            )
        if self._should_read_stdin():
            options.path_source = StreamReader(
                    sys.stdin,
                    self._get_file_list_separator()
                )
        scanner = scanning.scanner.Scanner(options)
        scanner.scan()
        return 0


def handle_repeated_interrupt(signal_number: int, stack) -> None:
    if parent_process() is None:
        print('Scan command terminating immediately...')
    os._exit(130)


def handle_interrupt(signal_number: int, stack) -> None:
    if parent_process() is None:
        print('Scan command interrupted, stopping...')
    signal.signal(signal.SIGINT, handle_repeated_interrupt)
    sys.exit(130)


signal.signal(signal.SIGINT, handle_interrupt)


def main(config) -> int:
    if config.extension_module_test:
        import helloModule
        helloModule.helloworld()
        sys.exit(0)

    command = None
    try:
        command = ScanCommand(config)
        command.execute()
        return 0
    except BaseException as exception:
        raise exception
        print(f'Error: {exception}')
        return 1
