import curses
import logging
import unicodedata
from typing import List, Optional, NamedTuple
from logging import Handler
from collections import deque, namedtuple

from wordfence.scanning.scanner import (ScanProgressUpdate, ScanMetrics,
                                        default_scan_finished_handler)
from ..banner.banner import get_welcome_banner
from ...util import timing

_displays = []

METRIC_BOX_WIDTH = 39
"""
Hard-coded width of metric boxes

The actual width taken up will be the hard-coded value +2 to account for the
left and right borders. Each box on the same row will be separated by the
padding value as well.
"""


class NullLogHandler(Handler):

    def __init__(self):
        Handler.__init__(self)

    def emit(self, record):
        pass


class NullStream:

    def write(self, line):
        pass


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
        window.addstr(f"{line}\n")
        window.refresh()


Position = namedtuple('Position', ['y', 'x'])


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
        self.window = None
        self.position = None

    def _initialize_window(self, y: int = 0, x: int = 0) -> None:
        height, width = self.compute_size()
        if self.parent is None:
            self.window = curses.newwin(height, width, y, x)
        else:
            self.window = self.parent.subwin(height, width, y, x)
        self.position = Position(y, x)
        self._post_initialize_window()

    def _post_initialize_window(self) -> None:
        pass

    def set_position(self, y: int, x: int) -> None:
        if self.window is None:
            self._initialize_window(y, x)
        else:
            try:
                self.window.mvwin(y, x)
                self.position = (y, x)
            except Exception:
                raise ValueError(f"error moving window: y: {y}, x: {x}; width:"
                                 f" {self.get_width()}; "
                                 f"height: {self.get_height()}")

    def _require_window(self) -> None:
        if self.window is None:
            self._initialize_window()

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
        self._require_window()
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


class MetricBox(Box):

    def __init__(
                self,
                metrics: List[Metric],
                title: Optional[str] = None,
                parent: Optional[curses.window] = None
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

    def __init__(
                self,
                banner,
                parent: Optional[curses.window] = None
            ):
        self.banner = banner
        super().__init__(parent, border=False)

    def get_width(self):
        # take the full width
        # return self.parent.getmaxyx()[1]
        return self.banner.column_count

    def get_height(self):
        return self.banner.row_count

    def draw_content(self):
        offset = self.get_border_offset()
        for index, row in enumerate(self.banner.rows):
            self.window.addstr(index + offset, offset, row)


class LogBox(Box):

    def __init__(
                self,
                columns: int,
                lines: int,
                parent: Optional[curses.window] = None
            ):
        self.columns = columns
        self.lines = lines
        self.messages = deque()
        self.cursor_position = None
        super().__init__(parent, border=True)

    def get_width(self):
        return self.columns

    def get_height(self):
        return self.lines

    def _post_initialize_window(self) -> None:
        pass

    def draw_content(self) -> None:
        offset = self.get_border_offset()
        line = offset
        line_length = 0
        for message in self.messages:
            message = message[:self.columns]
            line_length = len(message)
            message = message.ljust(self.columns)
            message = "".join(
                    ch for ch in message if unicodedata.category(ch)[0] != "C"
                )
            self.window.addstr(line, offset, message)
            line += 1
        self.cursor_offset = Position(line - 1, line_length)

    def add_message(self, message: str) -> None:
        self.messages.append(message)
        while len(self.messages) > self.lines:
            self.messages.popleft()
        self.update()

    def get_cursor_position(self) -> Position:
        y = 0
        x = 0
        if self.position is not None:
            y += self.position.y
            x += self.position.x
        if self.cursor_offset is not None:
            y += self.cursor_offset.y
            x += self.cursor_offset.x
        return Position(y, x)


class LogBoxHandler(Handler):

    def __init__(self, log_box: LogBox):
        self.log_box = log_box
        Handler.__init__(self)

    def emit(self, record):
        self.log_box.add_message(record.getMessage())


class LogBoxStream():

    def __init__(self, log_box: LogBox):
        self.log_box = log_box

    def write(self, line):
        self.log_box.add_message(line)


class BoxLayout:

    def __init__(self, lines: int, cols: int, padding: int = 1):
        self.lines = lines
        self.cols = cols
        self.padding = padding
        self.current_line = 0
        self._content = []
        self._unpositioned = []
        self.max_row_width = 0

    def add_box(self, box: Box) -> None:
        self._content.append(box)
        self._unpositioned.append(box)

    def add_break(self) -> None:
        self._content.append(None)
        self._unpositioned.append(None)

    def _position_row(self, row: list) -> list:
        positioned = []
        extra = []
        row_width = 0
        unpadded_row_width = 0
        row_height = 0
        for box in row:
            height, width = box.compute_size()
            required_width = width + self.padding
            if len(positioned) and (
                        len(extra) or
                        row_width + required_width > self.cols
                    ):
                extra.append(box)
            else:
                row_width += required_width
                unpadded_row_width += width
                row_height = max(row_height, height)
                positioned.append((box, height, width))
        box_count = len(positioned)
        padding = int((self.cols - unpadded_row_width) / (box_count + 1))
        padded_width = unpadded_row_width + padding * (box_count + 1)
        x = padding + int((self.cols - padded_width) / 2)
        final_row_width = 0
        previous_padding = 0
        for (box, height, width) in positioned:
            final_row_width += previous_padding
            y = self.current_line + round((row_height - height) / 2)
            box.set_position(y, x)
            x += width + padding
            final_row_width += width
            previous_padding = padding
            box.update()
        self.current_line += row_height + self.padding
        self.max_row_width = max(self.max_row_width, final_row_width)
        return extra

    def position(self, reset: bool = False) -> None:
        if reset:
            self.current_line = 0
        row = []
        items = self._content if reset else self._unpositioned
        for item in items:
            if item is None:
                row = self._position_row(row)
            else:
                row.append(item)
        while len(row):
            row = self._position_row(row)
        self._unpositioned = []


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
    METRICS_COUNT = 5
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
        self.banner_box = self._initialize_banner()
        self.metric_boxes = self._initialize_metric_boxes()
        self.layout = self._initialize_layout()
        self.log_box = self._initialize_log_box()
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
        return BannerBox(banner=banner, parent=self.stdscr)

    def _compute_rate(self, value: int, elapsed_time: float) -> int:
        if elapsed_time > 0:
            return int(value / elapsed_time)
        return 0

    def _get_metrics(
                self,
                update: ScanProgressUpdate,
                worker_index: Optional[int] = None
            ) -> List[Metric]:
        file_count = update.metrics.get_int_metric('counts', worker_index)
        byte_count = update.metrics.get_int_metric('bytes', worker_index)
        match_count = update.metrics.get_int_metric('matches', worker_index)
        file_rate = self._compute_rate(file_count, update.elapsed_time)
        byte_rate = self._compute_rate(byte_count, update.elapsed_time)
        metrics = [
                Metric('Files Processed', file_count),
                Metric('Bytes Processed', byte_count),
                Metric('Matches Found', match_count),
                Metric('Files / Second', file_rate),
                Metric('Bytes / Second', byte_rate)
            ]
        if len(metrics) > self.METRICS_COUNT:
            raise ValueError("Metrics count is out of sync")
        return metrics

    def _initialize_metric_boxes(self) -> List[MetricBox]:
        default_metrics = ScanMetrics(self.worker_count)
        default_update = ScanProgressUpdate(
                elapsed_time=0,
                metrics=default_metrics
            )
        boxes = []
        for index in range(0, self.worker_count + 1):
            if index == 0:
                worker_index = None
                title = 'Summary'
            else:
                worker_index = index - 1
                title = f'Worker {index}'
            box = MetricBox(
                    self._get_metrics(default_update, worker_index),
                    title=title,
                    parent=self.stdscr
                )
            boxes.append(box)
        return boxes

    def _initialize_log_box(self) -> LogBox:
        log_box = LogBox(
                    columns=self.layout.max_row_width - 2,
                    lines=curses.LINES - self.layout.current_line - 2,
                    parent=self.stdscr
                )
        self.layout.add_box(log_box)
        self.layout.position()
        return log_box

    def _initialize_layout(self) -> BoxLayout:
        layout = BoxLayout(curses.LINES, curses.COLS, self.METRICS_PADDING)
        if self.banner_box is not None:
            layout.add_box(self.banner_box)
        for index, box in enumerate(self.metric_boxes):
            layout.add_box(box)
            if index == 0:
                layout.add_break()
        layout.position()
        return layout

    def _display_metrics(self, update: ScanProgressUpdate) -> None:
        for index in range(0, self.worker_count + 1):
            box = self.metric_boxes[index]
            worker_index = None if index == 0 else index - 1
            box.metrics = self._get_metrics(update, worker_index)
            box.update()

    def handle_update(self, update: ScanProgressUpdate) -> None:
        curses.update_lines_cols()
        self._display_metrics(update)
        self.banner_box.render()
        self.refresh()

    @staticmethod
    def metric_boxes_per_row(columns: int, padding: int = METRICS_PADDING):
        per_row = columns // METRIC_BOX_WIDTH
        if per_row == 0:
            return 0
        display_length = (per_row * METRIC_BOX_WIDTH) + (padding * per_row - 1)
        return per_row if display_length <= columns else per_row - 1

    def get_log_handler(self) -> logging.Handler:
        return LogBoxHandler(self.log_box)

    def get_output_stream(self) -> StreamToWindow:
        return LogBoxStream(self.log_box)

    def scan_finished_handler(
                self, metrics: ScanMetrics,
                timer: timing.Timer
            ) -> None:
        default_scan_finished_handler(metrics, timer)
        self.log_box.add_message('Scan completed! Press any key to exit.')
        cursor_position = self.log_box.get_cursor_position()
        curses.curs_set(1)
        if cursor_position is not None:
            self.stdscr.move(cursor_position.y, cursor_position.x + 1)
