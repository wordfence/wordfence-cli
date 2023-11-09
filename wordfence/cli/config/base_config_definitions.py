from .defaults import INI_DEFAULT_PATH
from .config_items import config_definitions_to_config_map

from ..terms_management import TERMS_URL
from ..mailing_lists import MailingList

config_definitions = {
    "configuration": {
        "short_name": "c",
        "description": "Path to a configuration INI file to use.",
        "context": "CLI",
        "argument_type": "OPTION",
        "default": INI_DEFAULT_PATH
    },
    "banner": {
        "description": "Display the Wordfence banner in command output when "
                       "running in a TTY/terminal.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": True,
        "category": "Output Control"
    },
    "license": {
        "short_name": "l",
        "description": "Specify the license to use.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": None
    },
    "verbose": {
        "short_name": "v",
        "description": "Enable verbose logging. If not specified, verbose "
                       "logging will be enabled automatically if stdout is a "
                       "TTY.",
        "context": "ALL",
        "argument_type": "OPTIONAL_FLAG",
        "default": None,
        "category": "Logging"
    },
    "debug": {
        "short_name": "d",
        "description": "Enable debug logging.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": False,
        "category": "Logging"
    },
    "quiet": {
        "short_name": "q",
        "description": "Suppress all output other than scan results.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": False,
        "category": "Logging"
    },
    "color": {
        "description": "Enable ANSI escape sequences in output.",
        "context": "CLI",
        "argument_type": "OPTIONAL_FLAG",
        "default": None,
        "category": "Output Control"
    },
    "cache-directory": {
        "description": "A path to use for cache files.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": "~/.cache/wordfence",
        "category": "Caching"
    },
    "cache": {
        "description": "Whether or not to enable the cache.",
        "context": "ALL",
        "argument_type": "FLAG",
        "default": True,
        "category": "Caching"
    },
    "purge-cache": {
        "description": "Purge any existing values from the cache.",
        "context": "CLI",
        "argument_type": "FLAG",
        "default": False,
        "category": "Caching"
    },
    "version": {
        "description": "Display the version of Wordfence CLI.",
        "context": "CLI",
        "argument_type": "FLAG",
        "default": False
    },
    "help": {
        "short_name": "h",
        "description": "Display help information.",
        "context": "CLI",
        "argument_type": "FLAG",
        "default": False
    },
    "accept-terms": {
        "description": "Automatically accept the terms required to invoke "
                       "the specified command. The latest terms can be "
                       "viewed using the wordfence terms command  and found "
                       f"at {TERMS_URL}. Register to receive updated "
                       "Wordfence CLI Terms of Service via email at "
                       f"{MailingList.TERMS.registration_url}. Join our "
                       "WordPress Security mailing list at "
                       f"{MailingList.WORDPRESS_SECURITY.registration_url} to "
                       "get security alerts, news, and research directly to "
                       "your inbox.",
        "context": "CLI",
        "argument_type": "FLAG",
        "default": False
    },
    # Hidden options
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
    "wfi-url": {
        "description": "Base URL for accessing the Wordfence Intelligence API",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": None,
        "hidden": True
    },
}

config_map = config_definitions_to_config_map(config_definitions)
