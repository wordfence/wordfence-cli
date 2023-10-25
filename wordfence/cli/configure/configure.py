from ..subcommands import Subcommand


class ConfigureSubcommand(Subcommand):

    def invoke(self) -> int:
        configurer = self.context.configurer
        configurer.prompt_for_config()
        return 0


factory = ConfigureSubcommand
