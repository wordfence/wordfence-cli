import curses
import logging
import os
import unicodedata
from math import ceil
from typing import List, Optional, NamedTuple

from wordfence.scanning.scanner import (ScanProgressUpdate, ScanMetrics,
                                        get_scan_finished_messages)
from ..banner.banner import get_welcome_banner, should_show_welcome_banner
from ...logging.Handlers import CursesHandler
from ...util import timing
from ...logging import log

_displays = []

METRIC_BOX_WIDTH = 39
"""
Hard-coded width of metric boxes

The actual width taken up will be the hard-coded value +2 to account for the
left and right borders. Each box on the same row will be separated by the
padding value as well.
"""


def reset_terminal() -> None:
    for display in _displays:
        display.end()


def compute_center_offset(width: int, cols=None) -> int:
    if cols is None:
        cols = curses.COLS
    if width > cols:
        return 0
    return int((cols - width) / 2)


def compute_center_offset_str(string: str, cols=None) -> int:
    return compute_center_offset(len(string), cols)


class StreamToWindow:

    def __init__(self, window: curses.window, parent: curses.window):
        self.window = window
        self.parent = parent

    def write(self, line):
        window = self.window
        # strip control characters
        line = "".join(ch for ch in line if unicodedata.category(ch)[0] != "C")
        window.addstr(f"\n {line}")
        window.refresh()


class Box:

    def __init__(
                self,
                parent: Optional[curses.window] = None,
                border: bool = True,
                title: Optional[str] = None
            ):
        self.parent = parent
        self.border = border
        self.title = title
        self.window = self._initialize_window()
        self.render()

    def _initialize_window(self) -> curses.window:
        height, width = self.compute_size()
        if True or self.parent is None:
            window = curses.newwin(height, width, 0, 0)
        else:
            window = self.parent.subwin(height, width, 0, 0)
        return window

    def set_position(self, y: int, x: int) -> None:
        try:
            self.window.mvwin(y, x)
        except Exception:
            raise ValueError(f"error moving window: y: {y}, x: {x}; width:"
                             f" {self.get_width()}; "
                             f"height: {self.get_height()}")

    def compute_size(self) -> (int, int):
        height = self.get_height()
        width = self.get_width()
        if self.border:
            width += 2
            height += 2
        return (height, width)

    def resize(self) -> None:
        self.window.clear()
        self.window.refresh()
        height, width = self.compute_size()
        self.window.resize(height, width)

    def set_title(self, title: str) -> None:
        self.title = title

    def render(self) -> None:
        height, width = self.compute_size()
        if self.border:
            self.window.border()
        if self.title is not None:
            title_length = len(self.title)
            title_offset = 0
            if title_length < width:
                title_offset = int((width - title_length) / 2)
            self.window.addstr(0, title_offset, self.title)
        self.draw_content()

    def get_border_offset(self) -> int:
        return 1 if self.border else 0

    def draw_content(self) -> None:
        pass

    def update(self) -> None:
        self.render()
        self.window.syncup()
        self.window.noutrefresh()


class Metric:

    def __init__(self, label: str, value):
        self.label = label
        self.value = str(value)


class MessageBox(Box):
    def __init__(
                self,
                parent,
                height: int,
                title: Optional[str] = None
            ):
        self._height = height
        super().__init__(parent, title=title, border=False)
        self.window.scrollok(True)
        self.window.idlok(True)
        self.window.addstr(" Scan messages will display here")
        self.window.refresh()
        self.parent.refresh()

    def resize(self) -> None:
        pass

    def render(self) -> None:
        pass

    def get_width(self) -> int:
        return self.parent.getmaxyx()[1] - 2

    def get_height(self) -> int:
        return self._height

    def draw_content(self) -> None:
        pass

    def update(self) -> None:
        self.window.syncup()
        self.window.noutrefresh()


class MetricBox(Box):

    def __init__(
                self,
                parent,
                metrics: List[Metric],
                title: Optional[str] = None
            ):
        self.metrics = metrics
        super().__init__(parent, title=title)

    def get_width(self) -> int:
        return METRIC_BOX_WIDTH

    def get_height(self) -> int:
        return len(self.metrics)

    def draw_content(self) -> None:
        width = self.get_width()
        offset = self.get_border_offset()
        for index, metric in enumerate(self.metrics):
            line = index + offset
            self.window.addstr(line, offset, f'{metric.label}:')
            value_offset = offset + width - len(metric.value)
            self.window.addstr(line, value_offset, metric.value)


class BannerBox(Box):

    def __init__(self, parent, banner):
        self.banner = banner
        super().__init__(parent, border=False)

    def get_width(self):
        # take the full width
        return self.parent.getmaxyx()[1]

    def get_height(self):
        return self.banner.row_count

    def draw_content(self):
        offset = self.get_border_offset()
        for index, row in enumerate(self.banner.rows):
            self.window.addstr(index + offset, offset, row)


class BoxLayout:

    def __init__(self, lines: int, cols: int, padding: int = 1):
        self.lines = lines
        self.cols = cols
        self.padding = padding
        self.x = 0
        self.y = 0
        self.max_row_height = 0

    def position(self, box: Box) -> None:
        height, width = box.compute_size()
        # check for wrapping
        if self.cols - self.x < width:
            self.y += self.max_row_height + self.padding
            self.x = 0
            self.max_row_height = 0
        box.set_position(self.y, self.x)
        self.max_row_height = max(height, self.max_row_height)
        self.x += width + self.padding


class LayoutValues(NamedTuple):
    rows: int
    cols: int
    metrics_per_row: int
    metric_rows: int
    metric_height: int
    banner_height: int
    last_metric_line: int
    ideal_message_box_height: int


class ProgressDisplay:

    METRICS_PADDING = 1
    METRICS_COUNT = 3
    MIN_MESSAGE_BOX_HEIGHT = 4

    def __init__(self, worker_count: int):
        _displays.append(self)
        self.worker_count = worker_count
        self._setup_curses()

    def _setup_curses(self) -> None:
        self.stdscr = curses.initscr()
        self._setup_colors()
        curses.noecho()
        curses.curs_set(0)
        self.clear()
        # self.banner_offset = self.display_banner()
        self.banner_box = self._initialize_banner()
        self.metric_boxes = self._initialize_metric_boxes()
        self.message_box = self._initialize_message_box()
        self._initialize_layout()
        self.refresh()

    def _setup_colors(self) -> None:
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        self.color_brand = curses.color_pair(1)

    def clear(self):
        self.stdscr.clear()

    def refresh(self):
        self.stdscr.noutrefresh()
        curses.doupdate()

    def end_on_input(self):
        self.stdscr.getkey()
        self.end()

    def end(self):
        curses.endwin()
        _displays.remove(self)

    def _initialize_banner(self) -> Optional[BannerBox]:
        banner = get_welcome_banner()
        if banner is None:
            return None
        return BannerBox(self.stdscr, banner)

    def display_banner(self) -> int:
        banner = get_welcome_banner()
        offset = compute_center_offset(banner.column_count)
        for index, row in enumerate(banner.rows):
            self.stdscr.addstr(index, offset, row, self.color_brand)
        return index + 1

    def _get_metrics(self, metrics: ScanMetrics, worker_index: int) -> \
            List[Metric]:
        metrics = [
                Metric('Files Processed', metrics.counts[worker_index]),
                Metric('Bytes Processed', metrics.bytes[worker_index]),
                Metric('Matches Found', metrics.matches[worker_index]),
            ]
        if len(metrics) > self.METRICS_COUNT:
            raise ValueError("Metrics count is out of sync")
        return metrics

    def _initialize_message_box(self) -> MessageBox:
        layout_values = self._get_layout_values()
        # raise ValueError(layout_values)
        return MessageBox(self.stdscr,
                          layout_values.ideal_message_box_height,
                          "scan messages")

    def _initialize_metric_boxes(self) -> List[MetricBox]:
        default_metrics = ScanMetrics(self.worker_count)
        boxes = []
        for worker_index in range(0, self.worker_count):
            display_index = worker_index + 1
            box = MetricBox(
                    self.stdscr,
                    self._get_metrics(default_metrics, worker_index),
                    title=f'Worker {display_index}'
                )
            boxes.append(box)
        return boxes

    def _initialize_layout(self) -> None:
        layout = BoxLayout(curses.LINES, curses.COLS, self.METRICS_PADDING)
        if self.banner_box is not None:
            layout.position(self.banner_box)
            self.banner_box.update()
        for box in self.metric_boxes:
            layout.position(box)
            box.update()
        layout.position(self.message_box)
        self.message_box.update()
        self.refresh()

    def _display_metrics(self, metrics: ScanMetrics) -> None:
        for worker_index in range(0, self.worker_count):
            box = self.metric_boxes[worker_index]
            box.metrics = self._get_metrics(metrics, worker_index)
            box.update()

    def handle_update(self, update: ScanProgressUpdate) -> None:
        curses.update_lines_cols()
        self._display_metrics(update.metrics)
        self.refresh()

    @staticmethod
    def metric_boxes_per_row(columns: int, padding: int = METRICS_PADDING):
        per_row = columns // METRIC_BOX_WIDTH
        if per_row == 0:
            return 0
        display_length = (per_row * METRIC_BOX_WIDTH) + (padding * per_row - 1)
        return per_row if display_length <= columns else per_row - 1

    @staticmethod
    def get_layout_values(worker_count: int,
                          banner_height: Optional[int] = None,
                          cols: Optional[int] = None,
                          rows: Optional[int] = None):
        if banner_height is None:
            banner = get_welcome_banner()
            banner_height = len(banner.rows) + 1 if banner is not None else 0
        if cols is None or rows is None:
            _cols, _rows = os.get_terminal_size()
            cols = _cols if cols is None else cols
            rows = _rows if rows is None else rows
        # one line per metric + two for the top and bottom borders
        metric_height = ProgressDisplay.METRICS_COUNT + 2
        metrics_per_row = ProgressDisplay.metric_boxes_per_row(cols)
        metric_rows = ceil(worker_count / metrics_per_row)
        padding = (0 if banner_height == 0 else 3) + (metric_rows - 1)
        last_metric_line = ((metric_height * metric_rows) + banner_height +
                            padding) - 1
        ideal_message_box_height = 0
        top_and_bottom_adjustment = 2
        final_message_spaceholder = 2
        min_message_box_space = (ProgressDisplay.MIN_MESSAGE_BOX_HEIGHT +
                                 top_and_bottom_adjustment)
        if (last_metric_line + min_message_box_space +
                final_message_spaceholder <= rows):
            max_height = (rows - last_metric_line - top_and_bottom_adjustment
                          - final_message_spaceholder)

            ideal_message_box_height = max_height
        return LayoutValues(rows, cols, metrics_per_row, metric_rows,
                            metric_height, banner_height, last_metric_line,
                            ideal_message_box_height)

    def get_log_handler(self) -> logging.Handler:
        return CursesHandler(self.message_box.window, self.message_box.parent)

    def get_output_stream(self) -> StreamToWindow:
        return StreamToWindow(self.message_box.window, self.message_box.parent)

    @staticmethod
    def requirements_met(worker_count: int, show_banner: True):
        banner_height = None if should_show_welcome_banner(show_banner) else 0
        layout_values = ProgressDisplay.get_layout_values(
            worker_count, banner_height)
        # raise ValueError(layout_values)
        combined_height = (layout_values.last_metric_line +
                           layout_values.ideal_message_box_height)
        return (layout_values.rows >= combined_height and
                layout_values.ideal_message_box_height > 0 and
                layout_values.cols >= (METRIC_BOX_WIDTH + 2))

    def _get_layout_values(self) -> LayoutValues:
        rows, cols = self.stdscr.getmaxyx()
        worker_count = len(self.metric_boxes)
        banner_height = self.banner_box.get_height() if self.banner_box else 0
        return ProgressDisplay.get_layout_values(worker_count,
                                                 banner_height, cols, rows)

    def scan_finished_handler(
                self, metrics: ScanMetrics,
                timer: timing.Timer
            ) -> None:
        messages = get_scan_finished_messages(metrics, timer)
        vals = self._get_layout_values()
        vertical_offset = (vals.last_metric_line +
                           vals.ideal_message_box_height) + 1
        exit_message = "Press any key to exit"
        message_lines = ceil(len(messages.results) / vals.cols) + (
                        ceil(len(exit_message) / vals.cols))
        if (vertical_offset + message_lines) > vals.rows:
            vertical_offset = vals.rows - message_lines
        if messages.timeouts:
            log.warning(messages.timeouts)
        self.stdscr.move(vertical_offset, 0)
        self.stdscr.clrtobot()
        self.stdscr.addstr(vertical_offset, 0, messages.results)
        self.stdscr.addstr(vertical_offset + message_lines - 1, 0,
                           exit_message)
        self.stdscr.refresh()
