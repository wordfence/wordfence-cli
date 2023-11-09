from ..subcommands import Subcommand


class ConfigureSubcommand(Subcommand):

    def invoke(self) -> int:
        configurer = self.context.configurer
        configurer.overwrite = self.config.overwrite
        configurer.request_license = self.config.request_license
        configurer.workers = self.config.workers
        configurer.default = self.config.default
        configurer.prompt_for_config()
        return 0


factory = ConfigureSubcommand
