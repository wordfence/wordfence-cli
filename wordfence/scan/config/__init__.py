import inspect
from os import path

CONFIG_DEFINITIONS_FILENAME = 'config_definitions.json'
CONFIG_DEFINITIONS_PATH: str = path.dirname(
    inspect.getfile(inspect.currentframe())) + path.sep + CONFIG_DEFINITIONS_FILENAME
CLI_TITLE = 'Scan files'
CONFIG_SECTION_NAME = 'SCAN'
