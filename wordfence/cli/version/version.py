from ..subcommands import Subcommand


class VersionSubcommand(Subcommand):

    def invoke(self) -> int:
        self.context.display_version()
        return 0


factory = VersionSubcommand
