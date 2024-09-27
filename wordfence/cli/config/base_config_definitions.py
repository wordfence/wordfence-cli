from ...logging import LogLevel

from ..terms_management import TERMS_URL
from ..mailing_lists import EMAIL_SIGNUP_MESSAGE
from ..email import SmtpTlsMode

from .defaults import INI_DEFAULT_PATH
from .config_items import config_definitions_to_config_map

config_definitions = {
    "configuration": {
        "short_name": "c",
        "description": "Path to a configuration INI file to use.",
        "context": "CLI",
        "argument_type": "OPTION",
        "default": INI_DEFAULT_PATH,
        "meta": {
            "accepts_file": True
        }
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
    "email": {
        "short_name": "E",
        "description": (
                "Email address(es) to which to send reports.\n"
                "The output file will be attached to the email report "
                "when the --output-path option is used. (for supported "
                "subcommands)"
            ),
        "context": "ALL",
        "argument_type": "OPTION_REPEATABLE",
        "default": None,
        "meta": {
            "separator": ","
        },
        "category": "Email"
    },
    "email-from": {
        "description": "The From address to use when sending emails. If "
                       "not specified, the current username and hostname "
                       "will be used.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": None,
        "category": "Email"
    },
    "smtp-host": {
        "description": "The host name of the SMTP server to use for "
                       "sending email.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": None,
        "category": "Email"
    },
    "smtp-port": {
        "description": "The port of the SMTP server to use for sending "
                       "email.",
        "context": "ALL",
        "argument_type": "OPTION",
        "meta": {
            "value_type": int
        },
        "default": None,
        "category": "Email"
    },
    "smtp-tls-mode": {
        "description": "The SSL/TLS mode to use when communicating with "
                       f"the SMTP server. {SmtpTlsMode.NONE.value} "
                       f"disables TLS entirely. {SmtpTlsMode.SMTPS.value} "
                       "requires TLS for all communication while "
                       f"{SmtpTlsMode.STARTTLS.value} will negotiate TLS "
                       "if supported using the STARTTLS SMTP command.",
        "context": "ALL",
        "argument_type": "OPTION",
        "meta": {"valid_options": [mode.value for mode in SmtpTlsMode]},
        "default": SmtpTlsMode.STARTTLS.value,
        "category": "Email"
    },
    "smtp-user": {
        "description": "The username for authenticating with the SMTP "
                       "server.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": None,
        "category": "Email"
    },
    "smtp-password": {
        "description": "The password for authentication with the SMTP "
                       "server. This should generally be specified in an "
                       "INI file as including passwords as command line "
                       "arguments can expose them to other users on the "
                       "same system.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": None,
        "category": "Email"
    },
    "sendmail-path": {
        "description": "The path to the sendmail executable. This will be "
                       "used to send email if SMTP is not configured.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": "sendmail",
        "category": "Email"
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
    "prefix-log-levels": {
        "description": "Prefix log messages with their respective levels. "
                       "This is enabled by default when colored output is "
                       "not enabled.",
        "context": "CLI",
        "argument_type": "OPTIONAL_FLAG",
        "default": None,
        "category": "Logging"
    },
    "log-level": {
        "short_name": "L",
        "description": "Only log messages at or above the specified level.",
        "context": "CLI",
        "argument_type": "OPTION",
        "default": None,
        "meta": {
            "valid_options": [level.name for level in LogLevel]
        },
        "category": "Logging"
    },
    "cache-directory": {
        "description": "A path to use for cache files.",
        "context": "ALL",
        "argument_type": "OPTION",
        "default": b'~/.cache/wordfence',
        "category": "Caching",
        "meta": {
            "accepts_directory": True
        }
    },
    "cache": {
        "description": "Enable caching. Caching is enabled by default.",
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
                       f"at {TERMS_URL}. {EMAIL_SIGNUP_MESSAGE}",
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
