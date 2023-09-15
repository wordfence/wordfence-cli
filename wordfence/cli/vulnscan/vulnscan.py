from ...intel.vulnerabilities import VulnerabilityIndex
from ...util.caching import Cacheable, DURATION_ONE_DAY
from ...wordpress.site import WordpressSite
from ..subcommands import Subcommand


class VulnScanSubcommand(Subcommand):

    def _load_vulnerability_index(self) -> VulnerabilityIndex:
        def initialize_vulnerability_index() -> VulnerabilityIndex:
            client = self.context.get_wfi_client()
            vulnerabilities = client.fetch_scanner_vulnerability_feed()
            return VulnerabilityIndex(vulnerabilities)
        vulnerability_index = Cacheable(
                'vulnerability_index',
                initialize_vulnerability_index,
                DURATION_ONE_DAY
            )
        return vulnerability_index.get(self.cache)

    def _scan(
                self,
                path: str,
                vulnerability_index: VulnerabilityIndex
            ) -> None:
        pass
        site = WordpressSite(path)
        # TODO: Implement site scanning
        del site

    def invoke(self) -> int:
        vulnerability_index = self._load_vulnerability_index()
        for path in self.config.trailing_arguments:
            self._scan(path, vulnerability_index)
        return 0


factory = VulnScanSubcommand
