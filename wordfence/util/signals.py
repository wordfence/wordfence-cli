import signal


HANDLED_SIGNALS = [
        signal.SIGINT
    ]


_handlers = None


def reset():
    global _handlers
    if _handlers is None:
        _handlers = {}
        for signal_type in HANDLED_SIGNALS:
            _handlers[signal_type] = signal.getsignal(signal_type)
            signal.signal(signal_type, signal.SIG_DFL)


def restore():
    global _handlers
    for signal_type, handler in _handlers.items():
        signal.signal(signal_type, handler)
    _handlers = None
