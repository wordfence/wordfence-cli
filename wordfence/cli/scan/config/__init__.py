from typing import Dict, Any

from .config_definitions import config_definitions

CLI_TITLE = 'Scan files'
CONFIG_SECTION_NAME = 'SCAN'


def get_config_definitions() -> Dict[str, Dict[str, Any]]:
    return config_definitions
