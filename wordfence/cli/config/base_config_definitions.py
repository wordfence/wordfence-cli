from .defaults import INI_DEFAULT_PATH
from .config_items import config_definitions_to_config_map

config_definitions = {
    "configuration": {
        "short_name": "c",
        "description": "Path to a configuration INI file to use (defaults to"
                       f" \"{INI_DEFAULT_PATH}\").",
        "context": "CLI",
        "argument_type": "OPTION",
        "default": INI_DEFAULT_PATH
    },
    "banner": {
        "description": "Display the Wordfence banner in command output when "
                       "running in a TTY/terminal.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": True
    },
    "license": {
        "short_name": "l",
        "description": "Specify the license to use.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": None
    },
    "version": {
        "description": "Display the version of Wordfence CLI.",
        "context": "CLI",
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
    "noc1-url": {
        "description": "URL to use for accessing the NOC1 API.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": None,
        "hidden": True
    },
}

config_map = config_definitions_to_config_map(config_definitions)
