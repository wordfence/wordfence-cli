from ..version import __version__


def get_user_agent():
    return f"Wordfence-CLI/{__version__}"
