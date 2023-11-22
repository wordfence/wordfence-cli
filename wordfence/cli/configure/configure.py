from ..subcommands import Subcommand
from ..configurer import MIN_WORKERS


class ConfigureSubcommand(Subcommand):

    def invoke(self) -> int:
        configurer = self.context.configurer
        configurer.overwrite = self.config.overwrite
        configurer.request_license = self.config.request_license
        if self.config.workers is not None \
                and self.config.workers < MIN_WORKERS:
            if self.config.is_from_cli('workers'):
                raise ValueError(
                        'The number of workers cannot be less than '
                        f'{MIN_WORKERS}'
                    )
            self.config.workers = MIN_WORKERS
        configurer.workers = self.config.workers
        configurer.default = self.config.default
        configurer.prompt_for_config()
        return 0


factory = ConfigureSubcommand
