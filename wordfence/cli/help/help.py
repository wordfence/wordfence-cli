from ..subcommands import Subcommand


class HelpSubcommand(Subcommand):

    def invoke(self) -> int:
        self.config.display_help()
        return 0


factory = HelpSubcommand
