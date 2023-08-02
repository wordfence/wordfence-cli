import json

from wordfence.cli.config import load_config
from wordfence.cli.banner import welcome_banner

config = load_config()
print(f'Values passed to subcommand {json.dumps(config.subcommand)}:\n\n{config.values()}')

if config.banner:
    welcome_banner()
