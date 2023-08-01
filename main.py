import json

from wordfence.config import load_config

config = load_config()
print(f'Values passed to subcommand {json.dumps(config.subcommand)}:\n\n{config.values()}')
