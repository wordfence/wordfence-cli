import sys

from .banner.banner import show_welcome_banner_if_enabled
from .config import load_config
from .subcommands import import_subcommand_module, load_subcommand_definitions
from ..version import __version__
from ..util import pcre


def display_version() -> None:
    print(f"Wordfence CLI {__version__}")
    jit_support_text = 'Yes' if pcre.HAS_JIT_SUPPORT else 'No'
    print(f"PCRE Version: {pcre.VERSION} - JIT Supported: {jit_support_text}")


def main() -> int:
    subcommand_definitions = load_subcommand_definitions()

    config = load_config(subcommand_definitions)

    show_welcome_banner_if_enabled(config)

    if config.version:
        display_version()
        return 0

    if config.subcommand is None:
        config.display_help()
        return 0

    subcommand_module = import_subcommand_module(config.subcommand)
    return subcommand_module.main(config)


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
