import importlib
import sys

from .banner.banner import show_welcome_banner_if_enabled
from .config import load_config


def main():
    config = load_config()

    show_welcome_banner_if_enabled(config)

    subcommand_module = importlib.import_module(
            f'.{config.subcommand}.{config.subcommand}',
            package='wordfence.cli'
        )
    exit_code = subcommand_module.main(config)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
