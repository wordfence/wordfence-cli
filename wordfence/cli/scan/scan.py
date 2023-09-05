import sys
import signal
import os
import logging
from multiprocessing import parent_process
from contextlib import nullcontext
from typing import Any, Optional

from wordfence import scanning, api
from wordfence.api.licensing import LicenseSpecific
from wordfence.scanning import filtering
from wordfence.scanning.scanner import ExceptionContainer
from wordfence.util import caching, updater, pcre
from wordfence.util.io import StreamReader
from wordfence.intel.signatures import SignatureSet
from wordfence.logging import (log, remove_initial_handler,
                               restore_initial_handler)
from wordfence.version import __version__
from .reporting import Report, ReportFormat
from .configure import Configurer
from .progress import ProgressDisplay, ProgressException, reset_terminal


screen_handler: Optional[logging.Handler] = None


def revert_progress_changes() -> None:
    global screen_handler
    if screen_handler:
        log.removeHandler(screen_handler)
    restore_initial_handler()
    reset_terminal()


class ScanCommand:

    CACHEABLE_TYPES = {
            'wordfence.intel.signatures.SignatureSet',
            'wordfence.intel.signatures.CommonString',
            'wordfence.intel.signatures.Signature',
            'wordfence.api.licensing.License'
        }

    def __init__(self, config):
        self.config = config
        self.cache = self._initialize_cache()
        self.license = None
        self.cache.add_filter(self.filter_cache_entry)
        self.cacheable_signatures = None

    def filter_cache_entry(self, value: Any) -> Any:
        if isinstance(value, LicenseSpecific):
            if not value.is_compatible_with_license(self._get_license()):
                raise caching.InvalidCachedValueException(
                        'Incompatible license'
                    )
        return value

    def _get_license(self) -> api.licensing.License:
        if self.license is None:
            if self.config.license is None:
                raise api.licensing.LicenseRequiredException()
            self.license = api.licensing.License(self.config.license)
        return self.license

    def _initialize_cache(self) -> caching.Cache:
        if self.config.cache:
            try:
                return caching.CacheDirectory(
                        os.path.expanduser(self.config.cache_directory),
                        self.CACHEABLE_TYPES
                    )
            except caching.CacheException as e:
                log.warning('Failed to initialize cache directory: ' + str(e))
        return caching.RuntimeCache()

    def filter_signatures(self, signatures: SignatureSet) -> None:
        if self.config.include_signatures:
            for identifier in list(signatures.signatures.keys()):
                if identifier not in self.config.include_signatures:
                    signatures.remove_signature(identifier)
            for identifier in self.config.include_signatures:
                if identifier in signatures.signatures:
                    log.debug(f'Including signature: {identifier}')
                else:
                    log.warning(
                                f'Signature {identifier} was not found and '
                                'could not be included'
                            )
        if self.config.exclude_signatures is not None:
            for identifier in self.config.exclude_signatures:
                if signatures.remove_signature(identifier):
                    log.debug(f'Excluded signature {identifier}')
                else:
                    log.warning(
                            f'Signature {identifier} is not in the existing '
                            'set. It will not be used in the scan.'
                        )
        signature_count = len(signatures.signatures)
        log.debug(f'Filtered signature count: {signature_count}')

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

    def _should_write_stdout(self) -> bool:
        if sys.stdout is None or self.config.output is False:
            return False
        return self.config.output or self.config.output_path is None

    def _get_file_list_separator(self) -> str:
        if isinstance(self.config.file_list_separator, bytes):
            return self.config.file_list_separator.decode('utf-8')
        return self.config.file_list_separator

    def _initialize_file_filter(self) -> filtering.FileFilter:
        filter = filtering.FileFilter()
        has_include_overrides = False
        if self.config.include_files is not None:
            has_include_overrides = True
            for name in self.config.include_files:
                filter.add(filtering.filter_filename(name))
        if self.config.include_files_pattern is not None:
            has_include_overrides = True
            for pattern in self.config.include_files_pattern:
                filter.add(filtering.filter_pattern(pattern))
        if self.config.exclude_files is not None:
            for name in self.config.exclude_files:
                filter.add(filtering.filter_filename(name), False)
        if self.config.exclude_files_pattern is not None:
            for pattern in self.config.exclude_files_pattern:
                filter.add(filtering.filter_pattern(pattern), False)
        if not has_include_overrides:
            filter.add(filtering.filter_php)
            filter.add(filtering.filter_html)
            filter.add(filtering.filter_js)
            if self.config.images:
                filter.add(filtering.filter_images)
        return filter

    def _get_pcre_options(self) -> pcre.PcreOptions:
        return pcre.PcreOptions(
                    caseless=True,
                    match_limit=self.config.pcre_backtrack_limit,
                    match_limit_recursion=self.config.pcre_recursion_limit
                )

    def execute(self) -> int:
        if self.config.purge_cache:
            self.cache.purge()
        if self.config.check_for_update:
            updater.Version.check(self.cache)

        progress = None
        if self.config.progress:
            global screen_handler
            progress = ProgressDisplay(int(self.config.workers))
            screen_handler = progress.get_log_handler()
            remove_initial_handler()
            log.addHandler(screen_handler)

        paths = set()
        for argument in self.config.trailing_arguments:
            paths.add(argument)
        options = scanning.scanner.Options(
                paths=paths,
                workers=int(self.config.workers),
                signatures=self._get_signatures(),
                chunk_size=self.config.chunk_size,
                scanned_content_limit=int(self.config.scanned_content_limit),
                file_filter=self._initialize_file_filter(),
                match_all=self.config.match_all,
                pcre_options=self._get_pcre_options()
            )
        if self._should_read_stdin():
            options.path_source = StreamReader(
                    sys.stdin,
                    self._get_file_list_separator()
                )

        with open(self.config.output_path, 'w') if self.config.output_path \
                is not None else nullcontext() as output_file:
            output_format = ReportFormat(self.config.output_format)
            output_columns = self.config.output_columns
            report = Report(
                    output_format,
                    output_columns,
                    options.signatures,
                    self.config.output_headers
                )
            if self._should_write_stdout():
                if progress:
                    report.add_target(progress.get_output_stream())
                else:
                    report.add_target(sys.stdout)
            if output_file is not None:
                report.add_target(output_file)
            if not report.has_writers():
                log.error(
                        'Please specify an output file using the --output-path'
                        ' option or add --output to write results to standard '
                        'output'
                    )
                return 1
            self.scanner = scanning.scanner.Scanner(options)
            if progress:
                use_log_events = True
            else:
                use_log_events = False
            self.scanner.scan(
                    report.add_result,
                    progress.handle_update if progress is not None else None,
                    progress.scan_finished_handler if progress is not None
                    else None,
                    use_log_events
                )

            if progress:
                progress.end_on_input()
                revert_progress_changes()
                if progress.results_message:
                    print(progress.results_message)
        return 0

    def terminate(self) -> None:
        if hasattr(self, 'scanner') and self.scanner is not None:
            self.scanner.terminate()


def initialize_interrupt_handling(command: ScanCommand) -> None:

    def handle_interrupt(signal_number: int, stack) -> None:
        revert_progress_changes()
        if parent_process() is None:
            log.info('Scan command interrupted, stopping...')
            command.terminate()
            reset_terminal()
        sys.exit(130)

    signal.signal(signal.SIGINT, handle_interrupt)


def print_error(message: str) -> None:
    if sys.stderr is not None:
        print(message, file=sys.stderr)
    else:
        print(message)


def reset_terminal_with_error(message: str) -> None:
    reset_terminal()
    print_error(message)


def display_version() -> None:
    print(f"Wordfence CLI {__version__}")
    jit_support_text = 'Yes' if pcre.HAS_JIT_SUPPORT else 'No'
    print(f"PCRE Version: {pcre.VERSION} - JIT Supported: {jit_support_text}")


def main(config) -> int:
    command = None
    try:
        if config.version:
            display_version()
            return 0
        if config.quiet:
            log.setLevel(logging.CRITICAL)
        elif config.debug:
            log.setLevel(logging.DEBUG)
        elif config.verbose or (
                    config.verbose is None
                    and sys.stdout is not None and sys.stdout.isatty()
                ):
            log.setLevel(logging.INFO)
        configurer = Configurer(config)
        configurer.check_config()
        if not config.configure:
            command = ScanCommand(config)
            initialize_interrupt_handling(command)
            command.execute()
        return 0
    except api.licensing.LicenseRequiredException:
        reset_terminal_with_error('A valid Wordfence CLI license is required')
        return 1
    except BaseException as exception:
        if command is not None:
            command.terminate()
        reset_terminal()
        if isinstance(exception, ExceptionContainer):
            if config.debug:
                print_error(exception.trace)
                return 1
            exception = exception.exception
        if config.debug:
            raise exception
        else:
            if isinstance(exception, ProgressException):
                print_error(
                        'The current terminal size is inadequate for '
                        'displaying progress output for the current scan '
                        'options'
                    )
            elif isinstance(exception, SystemExit):
                raise exception
            else:
                print_error(f'Error: {exception}')
        return 1
