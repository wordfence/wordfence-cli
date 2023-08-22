import curses
import sys
from typing import List, Optional

from wordfence.scanning.scanner import ScanProgressUpdate, ScanMetrics, get_scan_finished_messages
from ..banner.banner import get_welcome_banner
from ...util import timing
from ...logging import log

_displays = []


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
        self.window.mvwin(y, x)

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
        self.resize()
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
                parent,
                metrics: List[Metric],
                title: Optional[str] = None
            ):
        self.metrics = metrics
        super().__init__(parent, title=title)

    def get_width(self) -> int:
        max_width = 0
        for metric in self.metrics:
            length = len(metric.label) + len(metric.value) + 2
            max_width = max(length, max_width)
        return max_width

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
        if self.cols - self.x < width:
            self.y += self.max_row_height + self.padding
            self.x = 0
            self.max_row_height = 0
        box.set_position(self.y, self.x)
        self.max_row_height = max(height, self.max_row_height)
        self.x += width + self.padding
        # self.y += height + self.padding


class ProgressDisplay:

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
        self.banner_box = self.initialize_banner()
        self.metric_boxes = self._initialize_metric_boxes()
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

    def initialize_banner(self) -> Optional[BannerBox]:
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

    def _get_metrics(self, metrics: ScanMetrics, worker_index: int) -> None:
        metrics = [
                Metric('Files Processed', metrics.counts[worker_index]),
                Metric('Bytes Processed', metrics.bytes[worker_index]),
                Metric('Matches Found', metrics.matches[worker_index]),
                Metric('Index', worker_index)
            ]
        return metrics

    def _initialize_metric_boxes(self) -> List[MetricBox]:
        default_metrics = ScanMetrics(self.worker_count)
        layout = BoxLayout(curses.LINES, curses.COLS)
        if self.banner_box is not None:
            layout.position(self.banner_box)
            self.banner_box.update()
        boxes = []
        for worker_index in range(0, self.worker_count):
            display_index = worker_index + 1
            box = MetricBox(
                    self.stdscr,
                    self._get_metrics(default_metrics, worker_index),
                    title=f'Worker {display_index}'
                )
            layout.position(box)
            box.update()
            boxes.append(box)
        self.refresh()
        return boxes

    def _display_metrics(self, metrics: ScanMetrics) -> None:
        layout = BoxLayout(curses.LINES, curses.COLS)
        if self.banner_box is not None:
            layout.position(self.banner_box)
            self.banner_box.update()
        for worker_index in range(0, self.worker_count):
            box = self.metric_boxes[worker_index]
            box.metrics = self._get_metrics(metrics, worker_index)
            layout.position(box)
            box.update()

    def handle_update(self, update: ScanProgressUpdate) -> None:
        curses.update_lines_cols()
        # elapsed = round(update.elapsed_time)
        # self.stdscr.addstr(
        #         curses.LINES - 1,
        #         0,
        #         f'Elapsed time: {elapsed}s'
        #     )
        # file_count = update.metrics.get_total_count()
        # byte_count = update.metrics.get_total_bytes()
        # match_count = update.metrics.get_total_matches()
        # timeout_count = update.metrics.get_total_timeouts()
        # speed = (byte_count / update.elapsed_time) if update.elapsed_time > 0 \
        #     else 0
        # stats = {
        #         'Files Processed': file_count,
        #         'Bytes Processed': byte_count,
        #         'Speed': speed,
        #         'Matches Found': match_count,
        #     }
        # if timeout_count > 0:
        #     stats['Signatures Timeouts'] = timeout_count
        # offset = self.banner_offset
        # for label, value in stats.items():
        #     self.stdscr.addstr(offset, 0, f'{label}: {value}')
        #     offset += 1
        self._display_metrics(update.metrics)
        self.refresh()

    def scan_finished_handler(self, metrics: ScanMetrics, timer: timing.Timer) -> None:
        messages = get_scan_finished_messages(metrics, timer)
        metric_height = 0
        for box in self.metric_boxes:
            max_y = box.get_height()
            metric_height = metric_height if metric_height > max_y else max_y
        banner_height = self.banner_box.get_height() if self.banner_box else 0
        padding = 2 if banner_height == 0 else 3
        if messages.timeouts:
            log.warning(messages.timeouts)
        self.stdscr.addstr(metric_height + banner_height + padding, 0,
                           messages.results)
        self.stdscr.refresh()
