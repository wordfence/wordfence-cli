import re
from typing import Dict, Any

from ..reporting import ReportFormat, ReportColumn
from wordfence.cli.config.defaults import INI_DEFAULT_PATH
from wordfence.util.pcre import PCRE_DEFAULT_MATCH_LIMIT, PCRE_DEFAULT_MATCH_LIMIT_RECURSION

KIBIBYTE = 1024
MEBIBYTE = 1024 * 1024

sizings_map = {
    'b': 1,
    'k': KIBIBYTE,
    'kb': KIBIBYTE,
    'kib': KIBIBYTE,
    'm': MEBIBYTE,
    'mb': MEBIBYTE,
    'mib': MEBIBYTE
}
"""maps suffixes to byte multipliers; k/kb/kib are synonyms, as are m/mb/mib"""


def byte_length(conversion_value: str) -> int:
    match = re.search(r"(\d+)([^0-9].*)", conversion_value)
    if not match:
        raise ValueError("Invalid format for byte length type")
    suffix = match.group(2).lower()
    if not sizings_map.get(suffix, False):
        raise ValueError("Unrecognized byte length suffix")
    return int(match.group(1)) * sizings_map.get(suffix)


config_definitions: Dict[str, Dict[str, Any]] = {
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
    "configuration": {
        "short_name": "c",
        "description": "Path to a configuration INI file to use (defaults to"
                       f" \"{INI_DEFAULT_PATH}\").",
        "context": "CLI",
        "argument_type": "OPTION",
        "default": INI_DEFAULT_PATH
    },
    "license": {
        "short_name": "l",
        "description": "Specify the license to use.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": None
    },
    "cache-directory": {
        "description": "A path to use for cache files.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": "~/.cache/wordfence"
    },
    "cache": {
        "description": "Whether or not to enable the cache.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": True
    },
    "purge-cache": {
        "description": "Purge any existing values from the cache.",
        "context": "CLI",
        "argument_type": "FLAG",
        "default": False
    },
    "verbose": {
        "short_name": "v",
        "description": "Enable verbose logging. If not specified, verbose "
                       "logging will be enabled automatically if stdout is a "
                       "TTY. Use --no-verbose to disable.",
        "context": "ALL",
        "argument_type": "OPTIONAL_FLAG",
        "default": None
    },
    "debug": {
        "short_name": "d",
        "description": "Enable debug logging.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": False
    },
    "quiet": {
        "short_name": "q",
        "description": "Suppress all output other than scan results.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": False
    },
    "banner": {
        "description": "Display the Wordfence banner in command output when "
                       "running in a TTY/terminal.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": True
    },
    "progress": {
        "description": "Display scan progress in the terminal with a curses "
                       "interface",
        "context": "CLI",
        "argument_type": "FLAG",
        "default": False
    },
    "configure": {
        "description": "Interactively configure Wordfence CLI.",
        "context": "CLI",
        "argument_type": "OPTIONAL_FLAG",
        "default": None
    },
    "version": {
        "description": "Display the version of Wordfence CLI.",
        "context": "CLI",
        "argument_type": "FLAG",
        "default": False
    },
    "check-for-update": {
        "description": "Whether or not to run the update check.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": True,
        "hidden": True
    },
    "noc1-url": {
        "description": "URL to use for accessing the NOC1 API.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": None,
        "hidden": True
    },
}
