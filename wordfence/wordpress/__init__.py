__all__ = ['site']


def __getattr__(name):
    if name == 'site':
        from . import site as module
        return module
    raise AttributeError(f"module {__name__} has no attribute {name}")
