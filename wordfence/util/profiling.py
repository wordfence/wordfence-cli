import time

from enum import Enum, auto
from typing import Dict, Optional, TextIO

from ..logging import log


class ProfileTimestamp:

    def __init__(self):
        self.clock_time = time.monotonic_ns()
        self.cpu_time = time.process_time_ns()


class TimeType(Enum):
    CLOCK = auto()
    CPU = auto()


class Timer:

    def __init__(self, time_type: TimeType, start: bool = True):
        self.time_type = time_type
        if start:
            self.start()
        else:
            self._start = None
        self._end = None

    def start(self) -> None:
        self._start = self._get_timestamp()

    def stop(self) -> None:
        self._end = self._get_timestamp()

    def _get_timestamp(self) -> int:
        raise NotImplementedError()

    def get_duration(self) -> int:
        if self._end is None or self._start is None or self._end < self._start:
            return 0
        return self._end - self._start


class ClockTimer(Timer):

    def __init__(self, start: bool = True):
        super().__init__(TimeType.CLOCK, start)

    def _get_timestamp(self) -> int:
        return time.monotonic_ns()


class CpuTimer(Timer):

    def __init__(self, start: bool = True):
        super().__init__(TimeType.CPU, start)

    def _get_timestamp(self) -> int:
        return time.process_time_ns()


def format_duration(duration: int) -> str:
    seconds = duration / 1000000000
    return str(round(seconds, 4)) + 's'


class ProfileEvent:

    def __init__(
                self,
                name: str,
                times: Dict[TimeType, int],
                is_global: bool = False
            ):
        self.name = name
        self.times = times
        self.is_global = is_global

    def get_time(self, time_type: TimeType = TimeType.CLOCK) -> Optional[int]:
        try:
            return self.times[time_type]
        except KeyError:
            return None

    def __str__(self) -> str:
        return ', '.join([
                type.name + ': ' + format_duration(time) for (type, time)
                in self.times.items()
            ])


def _get_times(*timers) -> Dict[TimeType, int]:
    times = {}
    for timer in timers:
        timer.stop()
        times[timer.time_type] = timer.get_duration()
    return times


class EventTimer:

    def __init__(self, name: str, start: bool = True, is_global: bool = False):
        self.name = name
        if start:
            self.start()
        else:
            self.clock_timer = None
            self.cpu_timer = None
        self.is_global = is_global

    def start(self) -> None:
        self.clock_timer = ClockTimer()
        self.cpu_timer = CpuTimer()

    def stop(self) -> Optional[ProfileEvent]:
        if self.clock_timer is None:
            return None
        return ProfileEvent(
                self.name,
                _get_times(self.clock_timer, self.cpu_timer),
                self.is_global
            )


class TimeAggregate:

    def __init__(self):
        self.average = 0
        self.min = None
        self.max = None
        self.total = 0
        self.count = 0

    def add(self, value: int) -> None:
        previous_count = self.count
        self.count += 1
        self.average = (
                (self.average * previous_count) + value
            ) / self.count
        self.min = value if self.min is None else min(self.min, value)
        self.max = value if self.max is None else max(self.max, value)
        self.total += value

    def __str__(self) -> str:
        average = format_duration(self.average)
        min = format_duration(self.min)
        max = format_duration(self.max)
        total = format_duration(self.total)
        return f'Total: {total}, Average: {average}, Min: {min}, Max: {max}'


class EventGroup:

    def __init__(self):
        self.events = []
        self.aggregates = {}

    def add(self, event: ProfileEvent) -> None:
        self.events.append(event)
        for time_type, duration in event.times.items():
            try:
                aggregate = self.aggregates[time_type]
            except KeyError:
                aggregate = TimeAggregate()
                self.aggregates[time_type] = aggregate
            aggregate.add(duration)


class ProfileWriter:

    def write(entry: str):
        raise NotImplementedError()


class LogProfileWriter(ProfileWriter):

    def __init__(self):
        self.write('=== PROFILING RESULTS ===')

    def write(self, entry: str):
        log.info(entry)


class FileProfileWriter(ProfileWriter):

    def __init__(self, file: TextIO):
        self.file = file

    def write(self, entry: str):
        self.file.write(entry)
        self.file.write('\n')


class ProfileWriterFactory:

    def __enter__(self) -> ProfileWriter:
        raise NotImplementedError()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        raise NotImplementedError()


class LogProfileWriterFactory(ProfileWriterFactory):

    def __enter__(self) -> ProfileWriter:
        return LogProfileWriter()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return


class FileProfileWriterFactory(ProfileWriterFactory):

    def __init__(self, path: str):
        self.path = path
        self.file = None

    def __enter__(self) -> ProfileWriter:
        self.file = open(self.path, 'w')
        return FileProfileWriter(self.file)

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.file.close()


class Profiler:

    def __init__(self):
        self.event_groups = {}
        self.global_events = EventGroup()
        self.timer = EventTimer('global', is_global=True)

    def complete(self) -> None:
        self.global_events.add(self.timer.stop())

    def add_event(self, event: ProfileEvent) -> None:
        try:
            group = self.event_groups[event.name]
        except KeyError:
            group = EventGroup()
            self.event_groups[event.name] = group
        group.add(event)
        if event.is_global:
            self.global_events.add(event)

    def _output_group(self, group: EventGroup, writer: ProfileWriter) -> None:
        for time_type, aggregate in group.aggregates.items():
            writer.write(f'\t{time_type.name}: {aggregate}')

    def output_results(self, writer: ProfileWriter) -> None:
        for name, group in self.event_groups.items():
            writer.write(f'{name}:')
            self._output_group(group, writer)
        writer.write('global:')
        self._output_group(self.global_events, writer)
