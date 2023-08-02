import json
import importlib
import sys

from wordfence.cli.banner import welcome_banner
from .config import load_config


def main():
    config = load_config()
    if config.banner:
        welcome_banner()

    subcommand_module = importlib.import_module(
            f'.{config.subcommand}.{config.subcommand}',
            package='wordfence.cli'
        )
    exit_code = subcommand_module.main(config)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
