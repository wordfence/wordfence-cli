from typing import Dict, Any

config_definitions: Dict[str, Dict[str, Any]] = {
    "configuration": {
        "short_name": "c",
        "description": "Path to a configuration INI file to use (defaults to"
                       " \"/etc/wordfence/wordfence-cli.ini\").",
        "context": "CLI",
        "argument_type": "OPTION",
        "default": "/etc/wordfence/wordfence-cli.ini"
    },
    "exclude-signatures": {
        "short_name": "i",
        "description": "Specify a rule ID to exclude from the scan. Can be "
                       "used multiple times.",
        "context": "ALL",
        "argument_type": "OPTION_REPEATABLE",
        "default": None,
        "meta": {
            "ini_separator": ",",
            "value_type": "int"
        }
    },
    "license": {
        "short_name": "l",
        "description": "Specify the license to use (usually stored in a "
                       "license file).",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": None
    },
    "read-stdin": {
        "description": "Sets default behavior of reading paths to scan from "
                       "stdin.",
        "context": "ALL",
        "argument_type": "FLAG",
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
    "report-path": {
        "short_name": "r",
        "description": "Write report out to this path.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": "./report.txt"
    },
    "report-format": {
        "short_name": "F",
        "description": "CSV or TSV. Defaults to \"CSV\".",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": "CSV",
        "meta": {
            "valid_options": (
                "csv",
                "tsv"
            )
        }
    },
    "threads": {
        "short_name": "t",
        "description": "Number of scanner threads (processes). Defaults to 1 "
                       "worker.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": 1
    },
    "output": {
        "description": "Write results to stdout.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": False
    },
    "output-format": {
        "short_name": "m",
        "description": "TODO determine output.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": None
    },
    "images": {
        "short_name": "g",
        "description": "PCRE regex pattern for image extensions. Defaults to "
                       "\"jpg|jpeg|mp3|avi|m4v|mov|mp4|gif|png|tiff?|svg|sql|"
                       "js|tbz2?|bz2?|xz|zip|tgz|gz|tar|log|err\\d+\".",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": "jpg|jpeg|mp3|avi|m4v|mov|mp4|gif|png|tiff?|svg|sql|js|"
                   "tbz2?|bz2?|xz|zip|tgz|gz|tar|log|err\\d+"
    },
    "include-files": {
        "short_name": "n",
        "description": "Only scan filenames that are exact matches. Can be "
                       "used multiple times.",
        "context": "ALL",
        "argument_type": "OPTION_REPEATABLE",
        "default": None,
        "meta": {
            "ini_separator": ","
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
            "ini_separator": ","
        }
    },
    "include-files-pattern": {
        "short_name": "N",
        "description": "PCRE regex allow pattern. Only matching filenames will"
                       " be scanned.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": None
    },
    "exclude-files-pattern": {
        "short_name": "X",
        "description": "PCRE regex deny pattern. Matching filenames will not "
                       "be scanned.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": None
    },
    "chunk-size": {
        "short_name": "z",
        "description": "Size of file chunks that will be scanned. Use a whole "
                       "number followed by one of the following suffixes: b "
                       "(byte), k (kibibyte), m (mebibyte).",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": "3m"
    },
    "max-file-size": {
        "short_name": "M",
        "description": "Files above this limit will not be scanned. Defaults"
                       " to 50 mebibytes. Use a whole number followed by one"
                       " config the following suffixes: b (byte), k (kibibyte)"
                       ", m (mebibyte).",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": "50m"
    },
    "automatic-resolution": {
        "short_name": "R",
        "description": "Automatic options the scan can take. This option can "
                       "be set multiple times to enable multiple resolutions. "
                       "Valid options: repair, delete, quarantine, "
                       "remove-permissions.",
        "context": "ALL",
        "argument_type": "OPTION_REPEATABLE",
        "default": None,
        "meta": {
            "valid_options": (
                "repair",
                "delete",
                "quarantine",
                "remove-permissions"
            ),
            "ini_separator": ","
        }
    },
    "banner": {
        "description": "Include to display the banner in command output.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": True
    },
    "cache-directory": {
        "description": "A path to use for cache files.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": "/var/cache/wordfence"
    },
    "noc1-url": {
        "description": "URL to use for accessing the NOC1 API.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": None,
        "hidden": True
    },
}
