import time


def unit_nanoseconds(ns: int) -> int:
    return ns


def unit_seconds(ns: int) -> int:
    return ns / 1000000000


def unit_milliseconds(ns: int) -> int:
    return ns / 1000000


class Timer:

    def __init__(self, start: bool = True):
        if start:
            self.start()
        else:
            self.start_time = None
        self.end_time = None
        self.previous_time = 0

    def _capture_time(self) -> int:
        return time.monotonic_ns()

    def start(self) -> None:
        self.start_time = self._capture_time()
        self.end_time = None

    def reset(self) -> None:
        self.start()

    def stop(self) -> None:
        self.end_time = self._capture_time()

    def resume(self) -> None:
        if self.start_time is not None:
            self.previous_time += self.get_elapsed(
                    unit=unit_nanoseconds,
                    total=False
                )
        self.start()

    def _get_current_elapsed(self) -> int:
        if self.start_time is None:
            return 0
        end_time = \
            self.end_time if self.end_time is not None \
            else self._capture_time()
        return end_time - self.start_time

    def get_elapsed(self, unit=unit_seconds, total: bool = True) -> int:
        previous_time = self.previous_time if total else 0
        return unit(previous_time + self._get_current_elapsed())
