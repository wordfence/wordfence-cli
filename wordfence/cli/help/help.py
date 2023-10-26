from ..subcommands import Subcommand


class HelpSubcommand(Subcommand):

    def invoke(self) -> int:
        subcommand = None
        for argument in self.config.trailing_arguments:
            if subcommand is not None:
                raise Exception('Please specify a single subcommand')
            subcommand = argument
        self.helper.display_help(subcommand)
        return 0


factory = HelpSubcommand
