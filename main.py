import json

from wordfence.config import Config

print(f'Values passed to subcommand {json.dumps(Config.subcommand)}: {Config.values()}')
