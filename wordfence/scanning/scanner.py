import os
import queue
import time
from ctypes import c_bool, c_uint
from enum import IntEnum
from multiprocessing import Queue, Process, Value
from dataclasses import dataclass
from typing import Set, Optional, Callable, Dict

from .exceptions import ScanningException
from .matching import Matcher, RegexMatcher
from .filtering import FileFilter, filter_any
from ..util import timing
from ..util.io import StreamReader
from ..intel.signatures import SignatureSet
from ..logging import log

MAX_PENDING_FILES = 1000  # Arbitrary limit
MAX_PENDING_RESULTS = 100
QUEUE_READ_TIMEOUT = 0
DEFAULT_CHUNK_SIZE = 1024 * 1024


class ScanConfigurationException(ScanningException):
    pass


@dataclass
class Options:
    paths: Set[str]
    signatures: SignatureSet
    threads: int = 1
    chunk_size: int = DEFAULT_CHUNK_SIZE
    path_source: Optional[StreamReader] = None
    max_file_size: Optional[int] = None
    file_filter: Optional[FileFilter] = None


class Status(IntEnum):
    LOCATING_FILES = 0
    PROCESSING_FILES = 1
    COMPLETE = 2
    FAILED = 3


class FileLocator:

    def __init__(self, path: str, queue: Queue, file_filter: FileFilter):
        self.path = path
        self.queue = queue
        self.file_filter = file_filter
        self.located_count = 0

    def search_directory(self, path: str):
        try:
            contents = os.scandir(path)
            for item in contents:
                if item.is_dir():
                    yield from self.search_directory(item.path)
                elif item.is_file():
                    if not self.file_filter.filter(item.path):
                        continue
                    self.located_count += 1
                    yield item.path
        except OSError as os_error:
            raise ScanningException('Directory search failed') from os_error

    def locate(self):
        # TODO: Handle links and prevent loops
        real_path = os.path.realpath(self.path)
        if os.path.isdir(real_path):
            for path in self.search_directory(real_path):
                log.debug(f'File added to scan queue: {path}')
                self.queue.put(path)
        else:
            self.queue.put(real_path)


class FileLocatorProcess(Process):

    def __init__(
                self,
                input_queue_size: int = 10,
                output_queue_size: int = MAX_PENDING_FILES,
                file_filter: FileFilter = None
            ):
        self._input_queue = Queue(input_queue_size)
        self.output_queue = Queue(output_queue_size)
        self.file_filter = file_filter \
            if file_filter is not None \
            else FileFilter([filter_any])
        self._path_count = 0
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
        try:
            while (path := self._input_queue.get()) is not None:
                locator = FileLocator(
                        path=path,
                        file_filter=self.file_filter,
                        queue=self.output_queue
                    )
                locator.locate()
            self.output_queue.put(None)
        except ScanningException as exception:
            self.output_queue.put(exception)


class ScanEventType(IntEnum):
    COMPLETED = 0
    FILE_QUEUE_EMPTIED = 1
    FILE_PROCESSED = 2
    EXCEPTION = 3
    FATAL_EXCEPTION = 4


class ScanEvent:

    # TODO: Define custom (more compact) pickle serialization format for this
    # class as a potential performance improvement

    def __init__(self, worker_index: int, type: int, data=None):
        self.worker_index = worker_index
        self.type = type
        self.data = data


class ScanWorker(Process):

    def __init__(
                self,
                index: int,
                status: Value,
                work_queue: Queue,
                result_queue: Queue,
                matcher: Matcher,
                chunk_size: int = DEFAULT_CHUNK_SIZE,
                max_file_size: Optional[int] = None
            ):
        self.index = index
        self._status = status
        self._work_queue = work_queue
        self._result_queue = result_queue
        self._matcher = matcher
        self._chunk_size = chunk_size
        self._working = True
        self._max_file_size = max_file_size
        self.complete = Value(c_bool, False)
        super().__init__(name=self._generate_name())

    def _generate_name(self) -> str:
        return 'worker-' + str(self.index)

    def work(self):
        self._working = True
        log.debug(f'Worker {self.index} started, PID:' + str(os.getpid()))
        while self._working:
            try:
                item = self._work_queue.get(timeout=QUEUE_READ_TIMEOUT)
                if item is None:
                    self._put_event(ScanEventType.FILE_QUEUE_EMPTIED)
                    self._complete()
                elif isinstance(item, BaseException):
                    self._put_event(
                            ScanEventType.FATAL_EXCEPTION,
                            {'exception': item}
                        )
                else:
                    self._process_file(item)
            except queue.Empty:
                if self._status.value == Status.PROCESSING_FILES:
                    self._complete()

    def _put_event(self, event_type: ScanEventType, data: dict = None) -> None:
        if data is None:
            data = {}
        self._result_queue.put(ScanEvent(self.index, event_type, data))

    def _complete(self):
        self._working = False
        self.complete.value = True
        self._put_event(ScanEventType.COMPLETED)

    def is_complete(self) -> bool:
        return self.complete.value

    def _has_exceeded_file_size_limit(self, length: int) -> bool:
        if self._max_file_size is None or self._max_file_size == 0:
            return False
        return length > self._max_file_size

    def _process_file(self, path: str):
        try:
            log.debug(f'Processing file: {path}')
            with open(path, mode='rb') as file, \
                    self._matcher.create_context() as context:
                length = 0
                while (chunk := file.read(self._chunk_size)):
                    length += len(chunk)
                    if self._has_exceeded_file_size_limit(length):
                        break
                    context.process_chunk(chunk)
                self._put_event(
                        ScanEventType.FILE_PROCESSED,
                        {
                            'path': path,
                            'length': length,
                            'matches': context.matches,
                            'timeouts': context.timeouts
                        }
                    )
        except OSError as error:
            self._put_event(ScanEventType.EXCEPTION, {'exception': error})

    def run(self):
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


class ScanWorkerPool:

    def __init__(
                self,
                size: int,
                work_queue: Queue,
                matcher: Matcher,
                metrics: ScanMetrics,
                chunk_size: int = DEFAULT_CHUNK_SIZE,
                max_file_size: Optional[int] = None
            ):
        self.size = size
        self._matcher = matcher
        self._work_queue = work_queue
        self.metrics = metrics
        self._chunk_size = chunk_size
        self._max_file_size = max_file_size
        self._started = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.stop()
        else:
            self.terminate()

    def start(self):
        if self._started:
            raise ScanningException('Worker pool has already been started')
        self._status = Value(c_uint, Status.LOCATING_FILES)
        self._result_queue = Queue(MAX_PENDING_RESULTS)
        self._workers = []
        for i in range(self.size):
            worker = ScanWorker(
                    i,
                    self._status,
                    self._work_queue,
                    self._result_queue,
                    self._matcher,
                    self._chunk_size,
                    self._max_file_size
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

    def terminate(self):
        self._assert_started()
        for worker in self._workers:
            worker.terminate()

    def is_complete(self) -> bool:
        self._assert_started()
        for worker in self._workers:
            if not worker.is_complete():
                return False
        return True

    def await_results(self, result_processor: Callable[[ScanResult], None]):
        self._assert_started()
        while True:
            event = self._result_queue.get()
            if event is None:
                log.debug('All workers have completed and all results have '
                          'been processed.')
                return
            elif event.type == ScanEventType.COMPLETED:
                log.debug(f'Worker {event.worker_index} completed')
                if self.is_complete():
                    self._result_queue.put(None)
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
                log.error(
                        'Exception occurred while processing file: ' +
                        str(event.data['exception'])
                    )
            elif event.type == ScanEventType.FATAL_EXCEPTION:
                self._status.value = Status.FAILED
                self.terminate()
                raise event.data['exception']

    def is_failed(self) -> bool:
        return self._status.value == Status.FAILED


class Scanner:

    def __init__(self, options: Options):
        self.options = options
        self.failed = 0

    def _handle_worker_error(self, error: Exception):
        self.failed += 1
        raise error

    def _initialize_worker(
                self,
                status: Value,
                work_queue: Queue,
                result_queue: Queue
            ):
        worker = ScanWorker(status, work_queue, result_queue)
        worker.work()

    def scan(self, result_processor: Callable[[ScanResult], None]):
        """Run a scan"""
        timer = timing.Timer()
        file_locator_process = FileLocatorProcess(
                file_filter=self.options.file_filter
            )
        file_locator_process.start()
        for path in self.options.paths:
            file_locator_process.add_path(path)
        worker_count = self.options.threads
        log.debug("Using " + str(worker_count) + " worker(s)...")
        matcher = RegexMatcher(self.options.signatures)
        metrics = ScanMetrics(worker_count)
        with ScanWorkerPool(
                    worker_count,
                    file_locator_process.output_queue,
                    matcher,
                    metrics,
                    self.options.chunk_size,
                    self.options.max_file_size
                ) as worker_pool:
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
        self.log_results(metrics, timer)

    def log_results(self, metrics: ScanMetrics, timer: timing.Timer) -> None:
        match_count = metrics.get_total_matches()
        total_count = metrics.get_total_count()
        byte_count = metrics.get_total_bytes()
        elapsed_time = timer.get_elapsed()
        timeout_count = metrics.get_total_timeouts()
        if timeout_count > 0:
            log.warning(f'{timeout_count} timeout(s) occurred during scan')
        log.info(
                f'Found {match_count} match(es) after processing {total_count}'
                f' file(s) containing {byte_count} byte(s) over {elapsed_time}'
                f' second(s)'
            )
