from ..subcommands import SubcommandDefinition, UsageExample
from ..config.typing import ConfigDefinitions
from ...api.intelligence import VulnerabilityFeedVariant
from .reporting import VULN_SCAN_REPORT_CONFIG_OPTIONS

config_definitions: ConfigDefinitions = {
    "read-stdin": {
        "description": "Read WordPress base paths from stdin. If not specified"
                       ", paths will automatically be read from stdin when "
                       "input is not from a TTY.",
        "context": "ALL",
        "argument_type": "OPTIONAL_FLAG",
        "default": None
    },
    "path-separator": {
        "short_name": "s",
        "description": "Separator used to delimit paths when reading from "
                       "stdin. Defaults to the null byte.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": "AA==",
        "default_type": "base64"
    },
    "wordpress-path": {
        "short_name": "w",
        "description": "Path to the root of a WordPress installation to scan"
                       " for core vulnerabilities.",
        "context": "CLI",
        "argument_type": "OPTION_REPEATABLE",
        "default": [],
        "meta": {
            "separator": ",",
            "accepts_directory": True
        }
    },
    "plugin-directory": {
        "short_name": "p",
        "description": "Path to a directory containing WordPress plugins to"
                       " scan for vulnerabilities.",
        "context": "CLI",
        "argument_type": "OPTION_REPEATABLE",
        "default": [],
        "meta": {
            "separator": ",",
            "accepts_directory": True
        }
    },
    "theme-directory": {
        "short_name": "t",
        "description": "Path to a directory containing WordPress themes to"
                       " scan for vulnerabilities.",
        "context": "CLI",
        "argument_type": "OPTION_REPEATABLE",
        "default": [],
        "meta": {
            "separator": ",",
            "accepts_directory": True
        }
    },
    "relative-content-path": {
        "short_name": "C",
        "description": "Alternate path of the wp-content directory relative "
                       "to the WordPress root.",
        "context": "ALL",
        "argument_type": "OPTION_REPEATABLE",
        "default": [],
        "meta": {
            "separator": ","
        }
    },
    "relative-plugins-path": {
        "short_name": "P",
        "description": "Alternate path of the wp-content/plugins directory "
                       "relative to the WordPress root.",
        "context": "ALL",
        "argument_type": "OPTION_REPEATABLE",
        "default": [],
        "meta": {
            "separator": ","
        }
    },
    "relative-mu-plugins-path": {
        "short_name": "M",
        "description": "Alternate path of the wp-content/mu-plugins directory "
                       "relative to the WordPress root.",
        "context": "ALL",
        "argument_type": "OPTION_REPEATABLE",
        "default": [],
        "meta": {
            "separator": ","
        }
    },
    **VULN_SCAN_REPORT_CONFIG_OPTIONS,
    "exclude-vulnerability": {
        "short_name": "e",
        "description": "Vulnerability UUIDs or CVE IDs to exclude from scan "
                       "results.",
        "context": "ALL",
        "argument_type": "OPTION_REPEATABLE",
        "default": [],
        "meta": {
            "separator": ","
        }
    },
    "include-vulnerability": {
        "short_name": "i",
        "description": "Vulnerabilitiy UUIDs or CVE IDs to include in scan "
                       "results.",
        "context": "ALL",
        "argument_type": "OPTION_REPEATABLE",
        "default": [],
        "meta": {
            "separator": ","
        }
    },
    "informational": {
        "short_name": "I",
        "description": "Include informational vulnerability records in "
                       "results.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": False
    },
    "feed": {
        "short_name": "f",
        "description": "The feed to use for vulnerability information. "
                       "The production feed provides all available "
                       "information fields. The scanner feed contains "
                       "only the minimum fields necessary to conduct a scan "
                       "and may be a better choice when detailed "
                       "vulnerability information is not needed.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": VulnerabilityFeedVariant.PRODUCTION.path,
        "meta": {
            "valid_options": [
                    variant.path for variant in VulnerabilityFeedVariant
                ]
        }
    },
    "require-path": {
        "description": "When enabled, an error will be issued if at least one "
                       "path to scan is not specified. This is the default "
                       "behavior when running in a terminal.",
        "context": "CLI",
        "argument_type": "OPTIONAL_FLAG",
        "default": None
    },
    "allow-nested": {
        "description": "When enabled (the default), WordPress installations "
                       "nested below other installations will also be "
                       "scanned for vulnerabilities.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": True
    },
    "allow-io-errors": {
        "description": "Allow scanning to continue if IO errors are "
                       "encountered. Sites that cannot be processed "
                       "due to IO errors will be skipped and a warning will "
                       "be logged. This is the default behavior.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": True
    }
}

cacheable_types = {
    'wordfence.intel.vulnerabilities.VulnerabilityIndex',
    'wordfence.intel.vulnerabilities.ScannerVulnerability',
    'wordfence.intel.vulnerabilities.ProductionVulnerability',
    'wordfence.intel.vulnerabilities.Software',
    'wordfence.intel.vulnerabilities.ProductionSoftware',
    'wordfence.intel.vulnerabilities.SoftwareType',
    'wordfence.intel.vulnerabilities.VersionRange',
    'wordfence.intel.vulnerabilities.CopyrightInformation',
    'wordfence.intel.vulnerabilities.Copyright',
    'wordfence.intel.vulnerabilities.Cwe',
    'wordfence.intel.vulnerabilities.Cvss'
}

examples = [
    UsageExample(
        'Scan the WordPress installation at /var/www/html for vulnerabilities',
        'wordfence vuln-scan /var/www/html'
    ),
    UsageExample(
        'Generate a CSV file containing vulnerabilities found after scanning '
        '/var/www/html',
        'wordfence vuln-scan --output-format csv --output-path '
        '/tmp/wfcli-results.csv --output-columns link /var/www/html'
    )
]

definition = SubcommandDefinition(
    name='vuln-scan',
    usage='[OPTIONS] [WORDPRESS_PATH]...',
    description='Scan WordPress installations for vulnerable software',
    config_definitions=config_definitions,
    config_section='VULN_SCAN',
    cacheable_types=cacheable_types,
    examples=examples,
    accepts_directories=True
)
