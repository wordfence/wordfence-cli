from ..subcommands import SubcommandDefinition
from ..config.typing import ConfigDefinitions

config_definitions: ConfigDefinitions = {
}

cacheable_types = {
    'wordfence.intel.vulnerabilities.VulnerabilityIndex',
    'wordfence.intel.vulnerabilities.ScannerVulnerability',
    'wordfence.intel.vulnerabilities.Software',
    'wordfence.intel.vulnerabilities.SoftwareType',
    'wordfence.intel.vulnerabilities.VersionRange',
    'wordfence.intel.vulnerabilities.CopyrightInformation',
    'wordfence.intel.vulnerabilities.Copyright'
}

definition = SubcommandDefinition(
    name='vuln-scan',
    description='Scan WordPress installations for vulnerable software',
    config_definitions=config_definitions,
    config_section='VULN_SCAN',
    cacheable_types=cacheable_types
)
