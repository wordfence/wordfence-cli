from typing import Dict

from ...intel.vulnerabilities import VulnerabilityIndex, Vulnerability
from ...util.caching import Cacheable, DURATION_ONE_DAY
from ...wordpress.site import WordpressSite
from ...logging import log
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
            ) -> Dict[str, Vulnerability]:
        site = WordpressSite(path)
        log.debug(f'Located WordPress files at {site.core_path}')
        vulnerabilities = {}
        version = site.get_version()
        log.info(f'WordPress Core Version: {version}')
        vulnerabilities.update(
                vulnerability_index.get_core_vulnerabilties(version)
            )
        for plugin in site.get_plugins():
            log.info(f'Plugin {plugin.slug}, version: {plugin.version}')
            vulnerabilities.update(
                    vulnerability_index.get_plugin_vulnerabilities(
                            plugin.slug,
                            plugin.version
                        )
                )
        for theme in site.get_themes():
            log.info(f'Theme {theme.slug}, version: {theme.version}')
            vulnerabilities.update(
                    vulnerability_index.get_theme_vulnerabilities(
                        theme.slug,
                        theme.version
                    )
                )
        return vulnerabilities

    def invoke(self) -> int:
        vulnerability_index = self._load_vulnerability_index()
        for path in self.config.trailing_arguments:
            log.info(f'Scanning site at {path}...')
            vulnerabilities = self._scan(path, vulnerability_index)
            for vulnerability in vulnerabilities.values():
                print(f'Vulnerability {vulnerability.identifier}')
            log.info(f'Found {len(vulnerabilities)} vulnerabilit(y|ies)')
        return 0


factory = VulnScanSubcommand
