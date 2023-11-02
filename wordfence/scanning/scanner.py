import os
import queue
import time
import traceback
from ctypes import c_bool, c_uint
from enum import IntEnum
from multiprocessing import Queue, Process, Value
from dataclasses import dataclass
from typing import Set, Optional, Callable, Dict, NamedTuple, Tuple, List
from logging import Handler

from .exceptions import ScanningException, ScanningIoException
from .matching import Matcher, RegexMatcher
from .filtering import FileFilter, filter_any
from ..util import timing
from ..util.io import StreamReader
from ..util.pcre import PcreOptions, PCRE_DEFAULT_OPTIONS, PcreJitStack
from ..util.units import scale_byte_unit
from ..intel.signatures import SignatureSet
from ..logging import log, remove_initial_handler, VERBOSE

MAX_PENDING_FILES = 1000  # Arbitrary limit
MAX_PENDING_RESULTS = 100
QUEUE_READ_TIMEOUT = 0
PROGRESS_UPDATE_INTERVAL = 100
DEFAULT_CHUNK_SIZE = 1024 * 1024
FILE_LOCATOR_WORKER_INDEX = 0
"""Used by the file locator process when sending events"""


class ExceptionContainer(Exception):

    def __init__(self, exception: BaseException, trace: str = None):
        self.exception = exception
        if trace is None:
            self.trace = traceback.format_exc()
        else:
            self.trace = trace
        message = str(self.exception)
        super().__init__(
                f'An exception occurred in a child process: {message}'
            )

    def __reduce__(self) -> Tuple:
        return (
                self.__class__,
                (
                    self.exception,
                    self.trace
                )
            )


class ScanConfigurationException(ScanningException):
    pass


class ScanEventType(IntEnum):
    COMPLETED = 0
    FILE_QUEUE_EMPTIED = 1
    FILE_PROCESSED = 2
    EXCEPTION = 3
    FATAL_EXCEPTION = 4
    PROGRESS_UPDATE = 5
    LOG_MESSAGE = 6


class EventQueueLogHandler(Handler):

    def __init__(self, event_queue: Queue, worker_index: int):
        self._event_queue = event_queue
        self._worker_index = worker_index
        Handler.__init__(self)

    def emit(self, record):
        data = {
                'level': record.levelno,
                'message': record.getMessage()
            }
        self._event_queue.put(
            ScanEvent(
                ScanEventType.LOG_MESSAGE,
                data,
                worker_index=self._worker_index
            )
        )


def use_event_queue_log_handler(event_queue: Queue, worker_index: int) -> None:
    handler = EventQueueLogHandler(
            event_queue,
            worker_index
        )
    remove_initial_handler()
    log.addHandler(handler)


@dataclass
class Options:
    paths: Set[str]
    signatures: SignatureSet
    workers: int = 1
    chunk_size: int = DEFAULT_CHUNK_SIZE
    path_source: Optional[StreamReader] = None
    scanned_content_limit: Optional[int] = None
    file_filter: Optional[FileFilter] = None
    match_all: bool = False
    pcre_options: PcreOptions = PCRE_DEFAULT_OPTIONS
    allow_io_errors: bool = False,
    debug: bool = False


class Status(IntEnum):
    LOCATING_FILES = 0
    PROCESSING_FILES = 1
    COMPLETE = 2
    FAILED = 3


class FileLocator:

    def __init__(
                self,
                path: str,
                queue: Queue,
                file_filter: FileFilter,
                allow_io_errors: bool = False
            ):
        self.path = path
        self.queue = queue
        self.file_filter = file_filter
        self.allow_io_errors = allow_io_errors
        self.located_count = 0
        self.skipped_count = 0

    def _is_loop(self, path: str, parents: Optional[List[str]] = None) -> bool:
        realpath = os.path.realpath(path)
        try:
            if os.path.samefile(path, realpath):
                log.warning(
                        f'Symlink pointing to itself detected at {path}'
                    )
                return True
        except OSError as error:
            if error.errno == 40:
                log.warning(
                        f'Symlink loop detected at {path}'
                    )
                return True
            raise
        if parents is not None:
            for parent in parents:
                if realpath == parent:
                    log.warning(
                            f'Recursive symlink detected at {path}'
                        )
                    return True
        return False

    def _get_all_parents(self, path: str) -> List[str]:
        parents = [path]
        while len(path) > 1:
            path = os.path.dirname(path)
            parents.append(path)
        return parents

    def _handle_io_error(self, error: OSError, path: str) -> None:
        detail = str(error)
        if self.allow_io_errors:
            log.warning(
                    f'Path {path} could not be scanned due to an IO error and '
                    f'will be skipped. ({detail})'
                )
        else:
            raise ScanningIoException(
                    f'Directory search of {path} failed ({detail})'
                ) from error

    def search_directory(self, path: str, parents: Optional[list] = None):
        try:
            if parents is None:
                parents = self._get_all_parents(path)
            contents = os.scandir(path)
        except OSError as os_error:
            self._handle_io_error(os_error, path)
            return
        for item in contents:
            try:
                if item.is_symlink() and self._is_loop(item.path, parents):
                    continue
                if item.is_dir():
                    yield from self.search_directory(
                            item.path,
                            parents + self._get_all_parents(item.path)
                        )
                elif item.is_file():
                    if not self.file_filter.filter(item.path):
                        self.skipped_count += 1
                        continue
                    self.located_count += 1
                    yield item.path
            except OSError as os_error:
                self._handle_io_error(os_error, item.path)

    def locate(self):
        real_path = os.path.realpath(self.path)
        if os.path.isdir(real_path):
            for path in self.search_directory(real_path):
                log.log(VERBOSE, f'File added to scan queue: {path}')
                self.queue.put(path)
        else:
            if not self._is_loop(self.path):
                self.queue.put(real_path)


class FileLocatorProcess(Process):

    def __init__(
                self,
                input_queue_size: int = 10,
                output_queue_size: int = MAX_PENDING_FILES,
                file_filter: FileFilter = None,
                use_log_events: bool = False,
                event_queue: Optional[Queue] = None,
                allow_io_errors: bool = False
            ):
        self._input_queue = Queue(input_queue_size)
        self.output_queue = Queue(output_queue_size)
        self.file_filter = file_filter \
            if file_filter is not None \
            else FileFilter([filter_any])
        if use_log_events and not event_queue:
            raise ValueError('Using log events requires an event queue')
        self._use_log_events = use_log_events
        self._event_queue = event_queue
        self.allow_io_errors = allow_io_errors
        self._path_count = 0
        self._skipped_count = Value('i', 0)
        super().__init__(name='file-locator')

    def add_path(self, path: str):
        self._path_count += 1
        log.info(f'Scanning path: {path}')
        self._input_queue.put(path)

    def finalize_paths(self):
        self._input_queue.put(None)
        if self._path_count < 1:
            raise ScanConfigurationException(
                    'At least one scan path must be specified'
                )

    def get_next_file(self):
        return self.output_queue.get()

    def run(self):
        if self._use_log_events:
            use_event_queue_log_handler(
                    self._event_queue,
                    FILE_LOCATOR_WORKER_INDEX
                )
        try:
            skipped_count = 0
            while (path := self._input_queue.get()) is not None:
                locator = FileLocator(
                        path=path,
                        file_filter=self.file_filter,
                        queue=self.output_queue,
                        allow_io_errors=self.allow_io_errors
                    )
                locator.locate()
                skipped_count += locator.skipped_count
        except ScanningException as exception:
            self.output_queue.put(ExceptionContainer(exception))
        self._skipped_count.value = skipped_count
        self.output_queue.put(None)

    def get_skipped_count(self) -> int:
        return self._skipped_count.value


class ScanEvent:

    # TODO: Define custom (more compact) pickle serialization format for this
    # class as a potential performance improvement

    def __init__(
                self,
                type: int,
                data=None,
                worker_index: Optional[int] = None
            ):
        self.type = type
        self.data = data
        self.worker_index = worker_index


class ScanProgressMonitor(Process):

    def __init__(self, status: Value, event_queue: Queue):
        super().__init__(name='progress-monitor')
        self._event_queue = event_queue
        self._status = status

    def is_scan_running(self) -> bool:
        status = self._status.value
        return status != Status.COMPLETE and status != Status.FAILED

    def run(self):
        interval = PROGRESS_UPDATE_INTERVAL / 1000  # MS to seconds
        while self.is_scan_running():
            time.sleep(interval)
            self._event_queue.put(ScanEvent(ScanEventType.PROGRESS_UPDATE))


class ScanWorker(Process):

    def __init__(
                self,
                index: int,
                status: Value,
                work_queue: Queue,
                event_queue: Queue,
                matcher: Matcher,
                chunk_size: int = DEFAULT_CHUNK_SIZE,
                scanned_content_limit: Optional[int] = None,
                use_log_events: bool = False,
                allow_io_errors: bool = False
            ):
        self.index = index
        self._status = status
        self._work_queue = work_queue
        self._event_queue = event_queue
        self._matcher = matcher
        self._chunk_size = chunk_size
        self._working = True
        self._scanned_content_limit = scanned_content_limit
        self._use_log_events = use_log_events
        self._allow_io_errors = allow_io_errors
        self.complete = Value(c_bool, False)
        super().__init__(name=self._generate_name())

    def _generate_name(self) -> str:
        return 'worker-' + str(self.index)

    def work(self):
        self._working = True
        log.debug(f'Worker {self.index} started, PID:' + str(os.getpid()))
        with PcreJitStack() as jit_stack:
            while self._working:
                try:
                    item = self._work_queue.get(timeout=QUEUE_READ_TIMEOUT)
                    if item is None:
                        self._put_event(ScanEventType.FILE_QUEUE_EMPTIED)
                        self._complete()
                    elif isinstance(item, ExceptionContainer):
                        if isinstance(item.exception, ScanningIoException):
                            self._put_io_error(item)
                        else:
                            self._put_event(
                                    ScanEventType.FATAL_EXCEPTION,
                                    {'exception': item}
                                )
                    else:
                        try:
                            self._process_file(item, jit_stack)
                        except OSError as error:
                            self._put_io_error(ExceptionContainer(error))
                except queue.Empty:
                    if self._status.value == Status.PROCESSING_FILES:
                        self._complete()

    def _put_event(self, event_type: ScanEventType, data: dict = None) -> None:
        if data is None:
            data = {}
        self._event_queue.put(
                ScanEvent(event_type, data, worker_index=self.index)
            )

    def _put_io_error(self, error) -> None:
        event_type = ScanEventType.EXCEPTION if self._allow_io_errors \
                else ScanEventType.FATAL_EXCEPTION
        self._put_event(
                event_type,
                {'exception': error}
            )

    def _complete(self):
        self._working = False
        self.complete.value = True
        self._put_event(ScanEventType.COMPLETED)

    def is_complete(self) -> bool:
        return self.complete.value

    def _get_next_chunk_size(self, length: int) -> int:
        if self._scanned_content_limit is None:
            return self._chunk_size
        elif length >= self._scanned_content_limit:
            return 0
        else:
            return min(self._scanned_content_limit - length, self._chunk_size)

    def _process_file(self, path: str, jit_stack: PcreJitStack):
        log.log(VERBOSE, f'Processing file: {path}')
        with open(path, mode='rb') as file, \
                self._matcher.create_context() as context:
            length = 0
            while (chunk_size := self._get_next_chunk_size(length)):
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                first = length == 0
                length += len(chunk)
                if context.process_chunk(chunk, first, jit_stack):
                    break
            self._put_event(
                    ScanEventType.FILE_PROCESSED,
                    {
                        'path': path,
                        'length': length,
                        'matches': context.matches,
                        'timeouts': context.timeouts
                    }
                )

    def run(self):
        if self._use_log_events:
            use_event_queue_log_handler(self._event_queue, self.index)
        self.work()


class ScanResult:

    def __init__(
                self,
                path: str,
                read_length: int,
                matches: Dict[int, str],
                timeouts: Set[int],
                timestamp: float = None
            ):
        self.path = path
        self.read_length = read_length
        self.matches = matches
        self.timeouts = timeouts
        self.timestamp = timestamp if timestamp is not None else time.time()

    def has_matches(self) -> bool:
        return len(self.matches) > 0

    def get_timeout_count(self) -> int:
        return len(self.timeouts)


class ScanMetrics:

    def __init__(self, worker_count: int):
        self.counts = self._initialize_int_metric(worker_count)
        self.bytes = self._initialize_int_metric(worker_count)
        self.matches = self._initialize_int_metric(worker_count)
        self.timeouts = self._initialize_int_metric(worker_count)
        self.skipped_files = 0

    def _initialize_int_metric(self, worker_count: int):
        return [0] * worker_count

    def record_result(self, worker_index: int, result: ScanResult):
        self.counts[worker_index] += 1
        self.bytes[worker_index] += result.read_length
        if result.has_matches():
            self.matches[worker_index] += 1
        self.timeouts[worker_index] += result.get_timeout_count()

    def _aggregate_int_metric(self, metric: list) -> int:
        total = 0
        for value in metric:
            total += value
        return total

    def get_total_count(self) -> int:
        return self._aggregate_int_metric(self.counts)

    def get_total_bytes(self) -> int:
        return self._aggregate_int_metric(self.bytes)

    def get_total_matches(self) -> int:
        return self._aggregate_int_metric(self.matches)

    def get_total_timeouts(self) -> int:
        return self._aggregate_int_metric(self.timeouts)

    def get_int_metric(self, metric: str, worker_index: Optional[int] = None):
        values = getattr(self, metric)
        if worker_index is not None:
            return values[worker_index]
        else:
            return self._aggregate_int_metric(values)


class ScanProgressUpdate:

    def __init__(self, elapsed_time: int, metrics: ScanMetrics):
        self.elapsed_time = elapsed_time
        self.metrics = metrics


ScanResultCallback = Callable[[ScanResult], None]
ProgressReceiverCallback = Callable[[ScanProgressUpdate], None]
ScanFinishedCallback = Callable[[ScanMetrics, timing.Timer], None]


class ScanFinishedMessages(NamedTuple):
    results: str
    timeouts: Optional[str]
    skipped: Optional[str]


def get_scan_finished_messages(
            metrics: ScanMetrics,
            timer: timing.Timer
        ) -> ScanFinishedMessages:
    match_count = metrics.get_total_matches()
    total_count = metrics.get_total_count()
    byte_value = scale_byte_unit(metrics.get_total_bytes())
    elapsed_time = round(timer.get_elapsed())
    timeout_count = metrics.get_total_timeouts()
    timeouts_message = None
    if timeout_count > 0:
        timeouts_message = f'{timeout_count} timeout(s) occurred during scan'
    results_message = (f'Found {match_count} suspicious file(s) after '
                       f'processing {total_count} file(s) containing '
                       f'{byte_value} over {elapsed_time} second(s)')

    if metrics.skipped_files > 0:
        skipped_message = (
                f'{metrics.skipped_files} file(s) were skipped as they did '
                'not match the configured include patterns. Use '
                '--include-all-files (or -a) to include all files in the scan.'
            )
    else:
        skipped_message = None

    return ScanFinishedMessages(
            results_message,
            timeouts_message,
            skipped_message
        )


def default_scan_finished_handler(
            metrics: ScanMetrics,
            timer: timing.Timer
        ) -> None:
    """Used as the default ScanFinishedCallback"""
    messages = get_scan_finished_messages(metrics, timer)
    if messages.timeouts:
        log.warning(messages.timeouts)
    if messages.skipped:
        log.warning(messages.skipped)
    log.info(messages.results)
    return messages


class ScanWorkerPool:

    def __init__(
                self,
                size: int,
                work_queue: Queue,
                event_queue: Queue,
                matcher: Matcher,
                metrics: ScanMetrics,
                timer: timing.Timer,
                progress_receiver: Optional[ProgressReceiverCallback] = None,
                chunk_size: int = DEFAULT_CHUNK_SIZE,
                scanned_content_limit: Optional[int] = None,
                use_log_events: bool = False,
                allow_io_errors: bool = False,
                debug: bool = False
            ):
        self.size = size
        self._matcher = matcher
        self._work_queue = work_queue
        self._event_queue = event_queue
        self.metrics = metrics
        self._timer = timer
        self._progress_receiver = progress_receiver
        self._chunk_size = chunk_size
        self._scanned_content_limit = scanned_content_limit
        self._started = False
        self._use_log_events = use_log_events
        self._allow_io_errors = allow_io_errors
        self._debug = debug

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.stop()
        else:
            self.terminate()

    def has_progress_receiver(self) -> bool:
        return self._progress_receiver is not None

    def _send_progress_update(self) -> None:
        if self.has_progress_receiver():
            update = ScanProgressUpdate(
                    elapsed_time=self._timer.get_elapsed(),
                    metrics=self.metrics
                )
            self._progress_receiver(update)
            self._progress_timer.reset()

    def _is_progress_update_due(self) -> bool:
        if self._progress_timer is None:
            return False
        elapsed = self._progress_timer.get_elapsed(
                timing.unit_milliseconds
            )
        return elapsed >= PROGRESS_UPDATE_INTERVAL

    def start(self):
        if self._started:
            raise ScanningException('Worker pool has already been started')
        self._status = Value(c_uint, Status.LOCATING_FILES)
        self._workers = []
        if self.has_progress_receiver():
            self._progress_timer = timing.Timer()
            self._monitor = ScanProgressMonitor(
                    self._status,
                    self._event_queue
                )
            self._monitor.start()
            self._send_progress_update()
        else:
            self._progress_timer = None
            self._monitor = None
        for i in range(self.size):
            worker = ScanWorker(
                    i,
                    self._status,
                    self._work_queue,
                    self._event_queue,
                    self._matcher,
                    self._chunk_size,
                    self._scanned_content_limit,
                    self._use_log_events,
                    self._allow_io_errors
                )
            worker.start()
            self._workers.append(worker)
        self._started = True

    def _assert_started(self):
        if not self._started:
            raise ScanningException('Worker pool has not been started')

    def stop(self):
        self._assert_started()
        for worker in self._workers:
            worker.join()
        if self._monitor is not None:
            self._monitor.join()

    def terminate(self):
        self._assert_started()
        for worker in self._workers:
            worker.terminate()
        if self._monitor is not None:
            self._monitor.terminate()

    def is_complete(self) -> bool:
        self._assert_started()
        for worker in self._workers:
            if not worker.is_complete():
                return False
        return True

    def await_results(
                self,
                result_processor: ScanResultCallback,
            ):
        self._assert_started()
        while True:
            event = self._event_queue.get()
            if event is None:
                log.debug('All workers have completed and all results have '
                          'been processed.')
                self._status.value = Status.COMPLETE
                self._send_progress_update()
                return
            elif event.type == ScanEventType.COMPLETED:
                if event.worker_index != FILE_LOCATOR_WORKER_INDEX:
                    log.debug(f'Worker {event.worker_index} completed')
                else:
                    log.debug("File locator process exited")
                if self.is_complete():
                    self._event_queue.put(None)
            elif event.type == ScanEventType.FILE_PROCESSED:
                result = ScanResult(
                        event.data['path'],
                        event.data['length'],
                        event.data['matches'],
                        event.data['timeouts']
                    )
                if result.get_timeout_count() > 0:
                    log.warning(
                            'The following signatures timed out while '
                            f'processing {result.path}: ' +
                            ', '.join({str(i) for i in result.timeouts})
                        )
                self.metrics.record_result(
                        event.worker_index,
                        result
                    )
                result_processor(result)
            elif event.type == ScanEventType.FILE_QUEUE_EMPTIED:
                self._status.value = Status.PROCESSING_FILES
            elif event.type == ScanEventType.EXCEPTION:
                exception = event.data['exception']
                detail = str(exception)
                if self._debug:
                    detail += exception.trace
                    detail = detail.strip()
                log.warning(
                        f'Exception occurred during scanning: {detail}'
                    )
            elif event.type == ScanEventType.FATAL_EXCEPTION:
                self._status.value = Status.FAILED
                self.terminate()
                raise event.data['exception']
            elif event.type == ScanEventType.PROGRESS_UPDATE:
                if self._is_progress_update_due():
                    self._send_progress_update()
            elif event.type == ScanEventType.LOG_MESSAGE:
                message: str = event.data['message']
                log.log(event.data['level'], message)

    def is_failed(self) -> bool:
        return self._status.value == Status.FAILED


class Scanner:

    def __init__(self, options: Options):
        self.options = options
        self.failed = 0
        self.active = []

    def _handle_worker_error(self, error: Exception):
        self.failed += 1
        raise error

    def scan(
                self,
                result_processor: ScanResultCallback,
                progress_receiver: Optional[ProgressReceiverCallback] = None,
                scan_finished_handler: ScanFinishedCallback =
                default_scan_finished_handler,
                use_log_events: bool = False
            ):
        """Run a scan"""
        timer = timing.Timer()
        event_queue = Queue(MAX_PENDING_RESULTS)
        file_locator_process = FileLocatorProcess(
                file_filter=self.options.file_filter,
                use_log_events=use_log_events,
                event_queue=event_queue if use_log_events else None,
                allow_io_errors=self.options.allow_io_errors
            )
        self.active.append(file_locator_process)
        file_locator_process.start()
        for path in self.options.paths:
            file_locator_process.add_path(path)
        worker_count = self.options.workers
        log.debug("Using " + str(worker_count) + " worker(s)...")
        matcher = RegexMatcher(
                    self.options.signatures,
                    match_all=self.options.match_all,
                    pcre_options=self.options.pcre_options
                )
        metrics = ScanMetrics(worker_count)
        with ScanWorkerPool(
                    size=worker_count,
                    work_queue=file_locator_process.output_queue,
                    event_queue=event_queue,
                    matcher=matcher,
                    metrics=metrics,
                    timer=timer,
                    progress_receiver=progress_receiver,
                    chunk_size=self.options.chunk_size,
                    scanned_content_limit=self.options.scanned_content_limit,
                    use_log_events=use_log_events,
                    allow_io_errors=self.options.allow_io_errors,
                    debug=self.options.debug
                ) as worker_pool:
            self.active.append(worker_pool)
            if self.options.path_source is not None:
                log.debug('Reading input paths...')
                while True:
                    path = self.options.path_source.read_entry()
                    if path is None:
                        break
                    file_locator_process.add_path(path)
            file_locator_process.finalize_paths()
            log.debug('Awaiting results...')
            worker_pool.await_results(result_processor)
        timer.stop()
        scan_finished_handler = scan_finished_handler if scan_finished_handler\
            else default_scan_finished_handler
        metrics.skipped_files = file_locator_process.get_skipped_count()
        scan_finished_handler(metrics, timer)

    def terminate(self) -> None:
        for active in self.active:
            active.terminate()
