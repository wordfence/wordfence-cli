from logging import Handler
import curses

# based on log handlers in core python logging/__init__.py


class CursesHandler(Handler):

    def __init__(self, window, parent):
        Handler.__init__(self)
        self.window: curses.window = window
        self.parent: curses.window = parent

    def emit(self, record):
        try:
            message = self.format(record)
            self.window.addstr(f"{message}\n")
            self.window.refresh()
            #self.parent.refresh()
        except Exception:
            self.handleError(record)
