import json

from wordfence.cli.config import load_config

config = load_config()
print(f'Values passed to subcommand {json.dumps(config.subcommand)}:'
      f'\n\n{config.values()}')
