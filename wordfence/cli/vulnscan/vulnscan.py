from ..subcommands import Subcommand


class VulnScanSubcommand(Subcommand):

    def invoke(self) -> int:
        print('Test')
        return 0


factory = VulnScanSubcommand
