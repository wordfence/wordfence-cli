import time


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

    def _capture_time(self) -> int:
        return time.monotonic_ns()

    def start(self):
        self.start_time = self._capture_time()

    def reset(self):
        self.start()

    def stop(self):
        self.end_time = self._capture_time()

    def get_elapsed(self, unit=unit_seconds):
        end_time = \
                self.end_time if self.end_time is not None \
                else self._capture_time()
        return unit(end_time - self.start_time)
