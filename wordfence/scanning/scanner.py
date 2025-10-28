import os
import queue
import time
import traceback
import dataclasses
from ctypes import c_bool, c_uint, c_char
from enum import IntEnum
from multiprocessing import Queue, Process, Value, Array, get_start_method
from dataclasses import dataclass
from typing import Set, Optional, Callable, Dict, NamedTuple, Tuple, List, \
    Union, BinaryIO
from logging import Handler

from .exceptions import ScanningException, ScanningIoException
from .matching import MatchEngine, MatchEngineOptions, Matcher, MatchWorkspace
from .filtering import FileFilter, filter_any
from ..util import timing
from ..util.io import StreamReader, is_symlink_loop, is_symlink_and_loop, \
    get_all_parents, PathSet
from ..util.direct_io import DirectIoBuffer, DirectIoReader
from ..util.units import scale_byte_unit
from ..logging import log, remove_initial_handler, VERBOSE
from ..util.profiling import Profiler, ProfileEvent, EventTimer, \
    LogProfileWriterFactory, FileProfileWriterFactory

MAX_PENDING_FILES = 1000  # Arbitrary limit
MAX_PENDING_RESULTS = 100
QUEUE_READ_TIMEOUT = 0
RESULT_QUEUE_READ_TIMEOUT = 1
PROGRESS_UPDATE_INTERVAL = 100
DEFAULT_CHUNK_SIZE = 1024 * 1024
PATH_NAME_LIMIT = 4096
FILE_LOCATOR_WORKER_INDEX = 0
"""Used by the file locator process when sending events"""


USES_FORK = get_start_method() == 'fork'


class ExceptionContainer(Exception):

    def __init__(self, exception: BaseException, trace: str = None):  # noqa: B042, E501
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
    PROFILE_EVENT = 7


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


class ScanProfileEvent(ScanEvent):

    def __init__(
                self,
                event: ProfileEvent,
                worker_index: Optional[int] = None
            ):
        super().__init__(ScanEventType.PROFILE_EVENT, event, worker_index)


def _put_profile_event(
            queue: Queue,
            event: Optional[Union[ProfileEvent, EventTimer]]
        ) -> None:
    if event is None:
        return
    if isinstance(event, EventTimer):
        event = event.stop()
    queue.put(ScanProfileEvent(event))


def _event_timer(
            condition: bool,
            name: str,
            is_global: bool = False
        ) -> Optional[EventTimer]:
    if not condition:
        return None
    return EventTimer(name, is_global=is_global)


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
    paths: Set[bytes]
    match_engine_options: MatchEngineOptions
    workers: int = 1
    chunk_size: int = DEFAULT_CHUNK_SIZE
    path_source: Optional[StreamReader] = None
    scanned_content_limit: Optional[int] = None
    file_filter: Optional[FileFilter] = None
    allow_io_errors: bool = False
    debug: bool = False
    logging_initializer: Callable[[], None] = None
    match_engine: MatchEngine = MatchEngine.get_default()
    profile: bool = False,
    profile_path: Optional[str] = None,
    direct_io: bool = False


class Status(IntEnum):
    LOCATING_FILES = 0
    PROCESSING_FILES = 1
    COMPLETE = 2
    FAILED = 3


class FileLocator:

    def __init__(
                self,
                path: bytes,
                queue: Queue,
                file_filter: FileFilter,
                allow_io_errors: bool = False,
                scanned_paths: Optional[PathSet] = None
            ):
        self.path = path
        self.queue = queue
        self.file_filter = file_filter
        self.allow_io_errors = allow_io_errors
        self.scanned_paths = scanned_paths if scanned_paths is not None \
            else PathSet()
        self.located_count = 0
        self.skipped_count = 0

    def _is_loop(
                self,
                path: bytes,
                parents: Optional[List[bytes]] = None
            ) -> bool:
        if is_symlink_loop(path, parents):
            log.warning('Symlink loop detected at ' + os.fsdecode(path))
            return True
        return False

    def _handle_io_error(self, error: OSError, path: bytes) -> None:
        detail = str(error)
        if self.allow_io_errors:
            log.warning(
                    'Path ' + os.fsdecode(path) + ' could not be scanned due '
                    f'to an IO error and will be skipped. ({detail})'
                )
        else:
            raise ScanningIoException(
                    f'Directory search of {path} failed ({detail})'
                ) from error

    def search_directory(self, path: bytes, parents: Optional[list] = None):
        try:
            if parents is None:
                parents = get_all_parents(path)
                self.scanned_paths.add(path)
            contents = os.scandir(path)
        except OSError as os_error:
            self._handle_io_error(os_error, path)
            return
        for item in contents:
            item_path = item.path
            try:
                if item.is_symlink():
                    item_path = os.path.realpath(item.path)
                    if item_path in self.scanned_paths:
                        continue
                    # This intentionally uses the unresolved path
                    if self._is_loop(item.path, parents):
                        continue
                if item.is_dir():
                    self.scanned_paths.add(item_path)
                    yield from self.search_directory(
                            item_path,
                            parents + get_all_parents(item_path)
                        )
                elif item.is_file():
                    if not self.file_filter.filter(item_path):
                        self.skipped_count += 1
                        continue
                    self.located_count += 1
                    yield item_path
            except OSError as os_error:
                self._handle_io_error(os_error, item_path)

    def _push_file(self, path: bytes) -> None:
        if path in self.scanned_paths:
            log.warning(
                    'Skipping already queued path: ' + os.fsdecode(path)
                )
        else:
            log.log(VERBOSE, 'File added to scan queue: ' + os.fsdecode(path))
            self.queue.put(path)
            self.scanned_paths.add(path)

    def locate(self):
        real_path = os.path.realpath(self.path)
        if os.path.isdir(real_path):
            for path in self.search_directory(real_path):
                self._push_file(path)
        else:
            if not is_symlink_and_loop(self.path):
                self._push_file(real_path)


class FileLocatorProcess(Process):

    def __init__(
                self,
                input_queue_size: int = 10,
                output_queue_size: int = MAX_PENDING_FILES,
                file_filter: FileFilter = None,
                use_log_events: bool = False,
                event_queue: Optional[Queue] = None,
                allow_io_errors: bool = False,
                logging_initializer: Callable[[], None] = None,
                profile: bool = False
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
        self._logging_initializer = logging_initializer
        self.profile = profile
        self._path_count = 0
        self._skipped_count = Value('i', 0)
        super().__init__(name='file-locator')

    def add_path(self, path: bytes) -> bool:
        try:
            self._input_queue.put(path, block=False)
            self._path_count += 1
            log.info('Scanning path: ' + os.fsdecode(path))
            return True
        except queue.Full:
            return False

    def finalize_paths(self) -> bool:
        try:
            self._input_queue.put(None, block=False)
        except queue.Full:
            return False
        if self._path_count < 1:
            raise ScanConfigurationException(
                    'At least one scan path must be specified'
                )
        return True

    def get_next_file(self):
        return self.output_queue.get()

    def _put_profile_event(
                self,
                event: Optional[Union[ProfileEvent, EventTimer]]
            ) -> None:
        if not self.profile:
            return
        _put_profile_event(self._event_queue, event)

    def run(self):
        timer = _event_timer(self.profile, 'file_locator_all', is_global=True)
        if self._logging_initializer is not None:
            self._logging_initializer()
        if self._use_log_events:
            use_event_queue_log_handler(
                    self._event_queue,
                    FILE_LOCATOR_WORKER_INDEX
                )
        try:
            skipped_count = 0
            scanned_paths = PathSet()
            while (path := self._input_queue.get()) is not None:
                path_timer = _event_timer(self.profile, 'file_locator_path')
                locator = FileLocator(
                        path=path,
                        file_filter=self.file_filter,
                        queue=self.output_queue,
                        allow_io_errors=self.allow_io_errors,
                        scanned_paths=scanned_paths
                    )
                locator.locate()
                skipped_count += locator.skipped_count
                self._put_profile_event(path_timer)
        except ScanningException as exception:
            self.output_queue.put(ExceptionContainer(exception))
        self._skipped_count.value = skipped_count
        self.output_queue.put(None)
        self._put_profile_event(timer)

    def get_skipped_count(self) -> int:
        return self._skipped_count.value


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
                allow_io_errors: bool = False,
                logging_initializer: Callable[[], None] = None,
                profile: bool = False,
                direct_io: bool = False
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
        self._logging_initializer = logging_initializer
        self._profile = profile
        self._opener = self._open_direct if direct_io else self._open
        self._direct_io = direct_io
        self.complete = Value(c_bool, lock=False)
        self.last_file = Array(c_char, PATH_NAME_LIMIT + 1, lock=False)
        self._timer = None
        super().__init__(name=self._generate_name())

    def _generate_name(self) -> str:
        return 'worker-' + str(self.index)

    def _open(self, path: str) -> BinaryIO:
        return open(path, 'rb')

    def _open_direct(self, path: str) -> DirectIoReader:
        return DirectIoReader(path, self._direct_io_buffer)

    def work(self):
        self._timer = _event_timer(
                self._profile,
                'scan_worker',
                is_global=True
            )
        if self._direct_io:
            self._direct_io_buffer = DirectIoBuffer(self._chunk_size)
        try:
            self._working = True
            self._matcher.prepare(thread=True)
            log.debug(f'Worker {self.index} started, PID:' + str(os.getpid()))
            with self._matcher.create_workspace() as workspace:
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
                            timer = _event_timer(self._profile, 'process_file')
                            try:
                                self._process_file(item, workspace)
                            except OSError as error:
                                self._put_io_error(ExceptionContainer(error))
                            except Exception as error:
                                self._put_error(ExceptionContainer(error))
                            self._put_profile_event(timer)
                    except queue.Empty:
                        if self._status.value == Status.PROCESSING_FILES:
                            self._complete()
        except Exception as error:
            self._put_error(ExceptionContainer(error))

    def _put_event(self, event_type: ScanEventType, data: dict = None) -> None:
        if data is None:
            data = {}
        self._event_queue.put(
                ScanEvent(event_type, data, worker_index=self.index),
            )

    def _put_error(self, error, fatal: bool = True) -> None:
        event_type = ScanEventType.FATAL_EXCEPTION if fatal \
                else ScanEventType.EXCEPTION
        self._put_event(
                event_type,
                {'exception': error}
            )

    def _put_io_error(self, error) -> None:
        self._put_error(error, not self._allow_io_errors)

    def _put_profile_event(
                self,
                event: Optional[Union[ProfileEvent, EventTimer]]
            ) -> None:
        _put_profile_event(self._event_queue, event)

    def _complete(self):
        self._working = False
        self.complete.value = True
        if self._timer is not None:
            self._put_profile_event(self._timer.stop())
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

    def _process_file(self, path: str, workspace: Optional[MatchWorkspace]):
        log.log(VERBOSE, 'Processing file: ' + os.fsdecode(path))
        self.last_file.value = path[:PATH_NAME_LIMIT] + b'\0'
        open_timer = _event_timer(self._profile, 'open_file')
        with self._opener(path) as file, \
                self._matcher.create_context() as context:
            self._put_profile_event(open_timer)
            length = 0
            while (chunk_size := self._get_next_chunk_size(length)):
                chunk_timer = _event_timer(self._profile, 'read_chunk')
                chunk = file.read(chunk_size)
                self._put_profile_event(chunk_timer)
                if not chunk:
                    break
                first = length == 0
                length += len(chunk)
                match_timer = _event_timer(self._profile, 'match_chunk')
                try:
                    if context.process_chunk(
                                chunk,
                                start=first,
                                workspace=workspace
                            ):
                        break
                finally:
                    self._put_profile_event(match_timer)
            context.finalize_content()
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
        if self._logging_initializer is not None:
            self._logging_initializer()
        if self._use_log_events:
            use_event_queue_log_handler(self._event_queue, self.index)
        self.work()


class ScanResult:

    def __init__(
                self,
                path: bytes,
                read_length: int,
                matches: Dict[int, bytes],
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
        self.failed_files = 0

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
ScanFinishedCallback = Callable[
        [ScanMetrics, timing.Timer, Optional[Profiler]], None
    ]


class ScanFinishedMessages(NamedTuple):
    results: str
    timeouts: Optional[str]
    skipped: Optional[str]
    failed: Optional[str]


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

    if metrics.failed_files > 0:
        failed_message = (
                f'Processing of {metrics.failed_files} file(s) failed'
            )
    else:
        failed_message = None

    return ScanFinishedMessages(
            results_message,
            timeouts_message,
            skipped_message,
            failed_message
        )


def default_scan_finished_handler(
            metrics: ScanMetrics,
            timer: timing.Timer,
        ) -> None:
    """Used as the default ScanFinishedCallback"""
    messages = get_scan_finished_messages(metrics, timer)
    if messages.timeouts:
        log.warning(messages.timeouts)
    if messages.skipped:
        log.warning(messages.skipped)
    if messages.failed:
        log.error(messages.failed)
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
                debug: bool = False,
                logging_initializer: Callable[[], None] = False,
                profiler: Optional[Profiler] = None,
                direct_io: bool = False
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
        self._logging_initializer = logging_initializer
        self._profiler = profiler
        self._direct_io = direct_io
        self._completed = False

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

    def _initialize_worker(self, index: int) -> ScanWorker:
        worker = ScanWorker(
                index,
                self._status,
                self._work_queue,
                self._event_queue,
                self._matcher,
                self._chunk_size,
                self._scanned_content_limit,
                self._use_log_events,
                self._allow_io_errors,
                self._logging_initializer,
                self._profiler is not None,
                self._direct_io
            )
        worker.start()
        return worker

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
            worker = self._initialize_worker(i)
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

    def check_workers(self) -> None:
        for worker in self._workers:
            if worker.exitcode is not None and worker.exitcode != 0:
                if len(worker.last_file.value) == 0:
                    raise Exception(
                            'Worker exited abnormally (code: '
                            f'{worker.exitcode}) before processing any file'
                        )
                else:
                    log.warning(
                            f'Worker exited abnormally (code: '
                            f'{worker.exitcode})  while processing '
                            + os.fsdecode(worker.last_file.value)
                        )
                    log.info(f'Restarting worker {worker.index}...')
                    self._workers[worker.index] = \
                        self._initialize_worker(worker.index)
                    self.metrics.failed_files += 1

    def await_results(
                self,
                result_processor: ScanResultCallback,
                final: bool = True
            ):
        if self._completed:
            return True
        self._assert_started()
        while True:
            try:
                self.check_workers()
                event = self._event_queue.get(
                        block=final,
                        timeout=RESULT_QUEUE_READ_TIMEOUT
                    )
            except queue.Empty:
                if final:
                    continue
                return False
            if event is None:
                log.debug('All workers have completed and all results have '
                          'been processed.')
                self._status.value = Status.COMPLETE
                self._send_progress_update()
                self._completed = True
                return True
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
                            'processing ' + os.fsdecode(result.path) + ':' +
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
                    detail += '\n' + exception.trace
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
            elif event.type == ScanEventType.PROFILE_EVENT:
                if self._profiler is not None:
                    self._profiler.add_event(event.data)
        return False

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

    def _initialize_matcher(self) -> Matcher:
        engine = self.options.match_engine
        options = dataclasses.replace(self.options.match_engine_options)
        options.lazy = not USES_FORK
        return engine.create_matcher(options)

    def scan(
                self,
                result_processor: ScanResultCallback,
                progress_receiver: Optional[ProgressReceiverCallback] = None,
                scan_finished_handler: ScanFinishedCallback =
                default_scan_finished_handler,
                use_log_events: bool = False
            ) -> ScanMetrics:
        """Run a scan"""
        timer = timing.Timer()
        profiler = Profiler() if self.options.profile else None
        event_queue = Queue(MAX_PENDING_RESULTS)
        file_locator_process = FileLocatorProcess(
                file_filter=self.options.file_filter,
                use_log_events=use_log_events,
                event_queue=event_queue if (
                        use_log_events or profiler is not None
                    ) else None,
                allow_io_errors=self.options.allow_io_errors,
                logging_initializer=self.options.logging_initializer,
                profile=profiler is not None
            )
        file_locator_process.start()
        self.active.append(file_locator_process)
        worker_count = self.options.workers
        if worker_count < 1:
            raise ScanConfigurationException(
                    'Scans require at least one worker'
                )
        log.debug("Using " + str(worker_count) + " worker(s)...")
        matcher = self._initialize_matcher()
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
                    debug=self.options.debug,
                    logging_initializer=self.options.logging_initializer,
                    profiler=profiler,
                    direct_io=self.options.direct_io
                ) as worker_pool:
            def add_path(path: str):
                while not file_locator_process.add_path(path):
                    worker_pool.await_results(result_processor, final=False)
            self.active.append(worker_pool)
            for path in self.options.paths:
                add_path(path)
            if self.options.path_source is not None:
                log.debug('Reading input paths...')
                while True:
                    path = self.options.path_source.read_entry()
                    if path is None:
                        break
                    add_path(os.fsencode(path))
            while not file_locator_process.finalize_paths():
                worker_pool.await_results(result_processor, final=False)
            log.debug('Awaiting results...')
            worker_pool.await_results(result_processor)
        timer.stop()
        scan_finished_handler = scan_finished_handler if scan_finished_handler\
            else default_scan_finished_handler
        metrics.skipped_files = file_locator_process.get_skipped_count()
        scan_finished_handler(metrics, timer)
        if profiler is not None:
            profiler.complete()
            if self.options.profile_path is None:
                writer_factory = LogProfileWriterFactory()
            else:
                writer_factory = FileProfileWriterFactory(
                        self.options.profile_path
                    )
            with writer_factory as writer:
                profiler.output_results(writer)
        return (metrics, timer)

    def terminate(self) -> None:
        for active in self.active:
            active.terminate()
