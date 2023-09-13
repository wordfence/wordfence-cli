from wordfence.util.pcre import PCRE_DEFAULT_MATCH_LIMIT, \
        PCRE_DEFAULT_MATCH_LIMIT_RECURSION
from wordfence.util.units import byte_length

from ..subcommands import SubcommandDefinition
from ..config.typing import ConfigDefinitions
from .reporting import ReportFormat, ReportColumn


config_definitions: ConfigDefinitions = {
    "read-stdin": {
        "description": "Read paths from stdin. If not specified, paths will "
                       "automatically be read from stdin when input is not "
                       "from a TTY. Specify --no-read-stdin to disable.",
        "context": "ALL",
        "argument_type": "OPTIONAL_FLAG",
        "default": None
    },
    "file-list-separator": {
        "short_name": "s",
        "description": "Separator used when listing files via stdin. Defaults "
                       "to the null byte.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": "AA==",
        "default_type": "base64"
    },
    "output": {
        "description": "Write results to stdout. This is the default behavior "
                       "when --output-path is not specified. Use --no-output "
                       "to disable.",
        "context": "ALL",
        "argument_type": "OPTIONAL_FLAG",
        "default": None
    },
    "output-path": {
        "description": "Path to which to write results.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": None,
    },
    "output-columns": {
        "description": ("An ordered, comma-delimited list of columns to"
                        " include in the output. Available columns: "
                        + ReportColumn.get_valid_options_as_string()),
        "context": "ALL",
        "argument_type": "OPTION",
        "default": "filename",
        "meta": {
            "separator": ","
        }
    },
    "output-format": {
        "short_name": "m",
        "description": "Output format used for result data.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": 'csv',
        "meta": {
            "valid_options": ReportFormat.get_valid_options()
        }
    },
    "output-headers": {
        "description": "Whether or not to include column headers in output",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": None
    },
    "exclude-signatures": {
        "short_name": "e",
        "description": "Specify rule IDs to exclude from the scan. Can be "
                       "comma-delimited and/or specified multiple times.",
        "context": "ALL",
        "argument_type": "OPTION_REPEATABLE",
        "default": None,
        "meta": {
            "separator": ",",
            "value_type": int
        }
    },
    "include-signatures": {
        "short_name": "i",
        "description": "Specify rule IDs to include in the scan. Can be "
                       "comma-delimited and/or specified multiple times.",
        "context": "ALL",
        "argument_type": "OPTION_REPEATABLE",
        "default": None,
        "meta": {
            "separator": ",",
            "value_type": int
        }
    },
    "images": {
        "description": "Include image files in the scan.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": False
    },
    "include-files": {
        "short_name": "n",
        "description": "Only scan filenames that are exact matches. Can be "
                       "used multiple times.",
        "context": "ALL",
        "argument_type": "OPTION_REPEATABLE",
        "default": None,
        "meta": {
            "separator": ","
        }
    },
    "exclude-files": {
        "short_name": "x",
        "description": "Do not scan filenames that are exact matches. Can be "
                       "used multiple times. Denials take precedence over "
                       "allows.",
        "context": "ALL",
        "argument_type": "OPTION_REPEATABLE",
        "default": None,
        "meta": {
            "separator": ","
        }
    },
    "include-files-pattern": {
        "short_name": "N",
        "description": "PCRE regex allow pattern. Only matching filenames will"
                       " be scanned.",
        "context": "ALL",
        "argument_type": "OPTION_REPEATABLE",
        "default": None,
        "meta": {
            "separator": ","
        }
    },
    "exclude-files-pattern": {
        "short_name": "X",
        "description": "PCRE regex deny pattern. Matching filenames will not "
                       "be scanned.",
        "context": "ALL",
        "argument_type": "OPTION_REPEATABLE",
        "default": None,
        "meta": {
            "separator": ","
        }
    },
    "allow-io-errors": {
        "description": "Allow scanning to continue if IO errors are "
                       "encountered. Files that cannot be read will "
                       "be skipped and a warning will be logged.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": False
    },
    "chunk-size": {
        "short_name": "z",
        "description": "Size of file chunks that will be scanned. Use a whole "
                       "number followed by one of the following suffixes: b "
                       "(byte), k (kibibyte), m (mebibyte). Defaults to 3m.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": 3145728,
        "meta": {
            "value_type": byte_length
        }
    },
    "scanned-content-limit": {
        "short_name": "M",
        "description": "The maximum amount of data to scan in each file."
                       " Content beyond this limit will not be scanned."
                       " Defaults to 50 mebibytes. Use a whole number followed"
                       " by one of the following suffixes: b (byte),"
                       " k (kibibyte), m (mebibyte).",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": byte_length('50m'),
        "meta": {
            "value_type": byte_length
        }
    },
    "match-all": {
        "description": "If set, all possible signatures will be checked "
                       "against each scanned file. Otherwise, only the "
                       "first matching signature will be reported",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": False
    },
    "pcre-backtrack-limit": {
        "description": "The regex backtracking limit for signature evaluation",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": PCRE_DEFAULT_MATCH_LIMIT,
        "meta": {
            "value_type": int
        }
    },
    "pcre-recursion-limit": {
        "description": "The regex recursion limit for signature evaluation",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": PCRE_DEFAULT_MATCH_LIMIT_RECURSION,
        "meta": {
            "value_type": int
        }
    },
    "workers": {
        "short_name": "w",
        "description": "Number of worker processes used to perform scanning. "
                       "Defaults to 1 worker process.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": 1
    },
    "progress": {
        "description": "Display scan progress in the terminal with a curses "
                       "interface",
        "context": "CLI",
        "argument_type": "FLAG",
        "default": False
    },
}


cacheable_types = {
    'wordfence.intel.signatures.SignatureSet',
    'wordfence.intel.signatures.CommonString',
    'wordfence.intel.signatures.Signature',
    'wordfence.api.licensing.License'
}

definition = SubcommandDefinition(
    name='scan',
    description='Scan files for malware',
    config_definitions=config_definitions,
    config_section='SCAN',
    cacheable_types=cacheable_types
)
