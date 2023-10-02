import sys
import signal
import logging
from multiprocessing import parent_process
from typing import Optional

from wordfence import scanning
from wordfence.scanning import filtering
from wordfence.util import caching, pcre
from wordfence.intel.signatures import SignatureSet
from wordfence.logging import (log, remove_initial_handler,
                               restore_initial_handler)
from ..subcommands import Subcommand
from .reporting import ScanReport, ScanReportFormat, ScanReportManager
from .progress import ProgressDisplay, ProgressException, reset_terminal


screen_handler: Optional[logging.Handler] = None


def revert_progress_changes() -> None:
    global screen_handler
    if screen_handler:
        log.removeHandler(screen_handler)
    restore_initial_handler()
    reset_terminal()


class ScanSubcommand(Subcommand):

    def _filter_signatures(
                self,
                signatures: SignatureSet,
            ) -> None:
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
        def fetch_signatures() -> SignatureSet:
            noc1_client = self.context.get_noc1_client()
            return noc1_client.get_malware_signatures()
        self.cacheable_signatures = caching.Cacheable(
                'signatures',
                fetch_signatures,
                caching.DURATION_ONE_DAY
            )
        signatures = self.cacheable_signatures.get(self.cache)
        self._filter_signatures(signatures)
        return signatures

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

    def _initialize_interrupt_handling(self) -> None:

        def handle_interrupt(signal_number: int, stack) -> None:
            revert_progress_changes()
            if parent_process() is None:
                log.info('Scan command interrupted, stopping...')
                self.terminate()
                reset_terminal()
            sys.exit(130)

        signal.signal(signal.SIGINT, handle_interrupt)

    def invoke(self) -> int:
        self._initialize_interrupt_handling()
        signatures = self._get_signatures()
        report_manager = ScanReportManager(
                self.config,
                signatures
            )
        io_manager = report_manager.get_io_manager()

        progress = None
        if self.config.progress:
            global screen_handler
            progress = ProgressDisplay(int(self.config.workers))
            screen_handler = progress.get_log_handler()
            if sys.stderr is None or sys.stderr.isatty():
                remove_initial_handler()
            log.addHandler(screen_handler)
            report_manager.set_progress_display(progress)

        paths = set()
        for argument in self.config.trailing_arguments:
            paths.add(argument)
        options = scanning.scanner.Options(
                paths=paths,
                workers=int(self.config.workers),
                signatures=signatures,
                chunk_size=self.config.chunk_size,
                scanned_content_limit=int(self.config.scanned_content_limit),
                file_filter=self._initialize_file_filter(),
                match_all=self.config.match_all,
                pcre_options=self._get_pcre_options(),
                allow_io_errors=self.config.allow_io_errors,
                debug=self.config.debug
            )
        if io_manager.should_read_stdin():
            options.path_source = io_manager.get_input_reader()

        with report_manager.open_output_file() as output_file:
            report = report_manager.initialize_report(
                    output_file
                )
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
        reset_terminal()

    def generate_exception_message(
                self,
                exception: BaseException
            ) -> Optional[str]:
        if isinstance(exception, ProgressException):
            return (
                    'The current terminal size is inadequate for '
                    'displaying progress output for the current scan '
                    'options'
                )
        return super().generate_exception_message(exception)


factory = ScanSubcommand
