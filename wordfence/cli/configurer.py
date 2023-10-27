from collections import namedtuple
from configparser import ConfigParser, DuplicateSectionError
from multiprocessing import cpu_count
from typing import Optional, List, Dict, TextIO

from wordfence.util.input import prompt, prompt_yes_no, prompt_int, \
        InvalidInputException
from wordfence.util.io import ensure_directory_is_writable, \
        ensure_file_is_writable, resolve_path, IoException
from wordfence.api import noc1
from wordfence.api.licensing import License, LICENSE_URL
from wordfence.api.exceptions import ApiException
from wordfence.logging import log
from .config import load_config
from .subcommands import SubcommandDefinition
from .terms import TERMS_URL, TermsManager
from .helper import Helper


CONFIG_SECTION_DEFAULT = 'DEFAULT'
LEGACY_CONFIG_SECTION = 'SCAN'
LEGACY_CONFIG_KEYS = {
        'license',
        'cache_directory',
        'workers'
    }
LEGACY_CONVERSION_SECTION = 'MALWARE_SCAN'


ConfigValue = namedtuple('ConfigValue', ['section', 'key', 'value'])


class ConfigFileManager:

    def __init__(
                self,
                config
            ):
        self.config = config
        self.parser = None
        self._read = False

    def initialize_parser(self) -> None:
        self.parser = ConfigParser()
        self._read = False

    def require_parser(self) -> None:
        if self.parser is None:
            self.initialize_parser()

    def require_section(self, section: str) -> None:
        self.require_parser()
        if section == CONFIG_SECTION_DEFAULT:
            return
        if self.parser.has_section(section):
            return
        try:
            self.parser.add_section(section)
        except DuplicateSectionError:
            pass

    def apply_update(self, update: ConfigValue) -> None:
        self.require_parser()
        self.require_section(update.section)
        self.parser.set(update.section, update.key, update.value)

    def resolve_ini_path(self) -> str:
        ini_path = self.config.ini_path if self.config.has_ini_file() \
            else self.config.configuration
        return resolve_path(ini_path)

    def read_existing_config(self, file: TextIO, ini_path: str) -> None:
        try:
            if not self._read:
                self.parser.read_file(file)
        except BaseException:
            log.warning(
                    'Failed to read existing config file at '
                    f'{ini_path}. existing data will be truncated.'
                )
        self._read = True

    def write(self, updates: List[ConfigValue]) -> None:
        # TODO: What if the INI file changes after the config is loaded?
        self.require_parser()
        ini_path = self.resolve_ini_path()
        ensure_file_is_writable(ini_path)
        open_mode = 'r' if self.config.has_ini_file() else 'w'
        with open(ini_path, open_mode + '+') as file:
            if self.config.has_ini_file():
                self.read_existing_config(file, ini_path)

            for update in updates:
                self.apply_update(update)

            file.truncate(0)
            file.seek(0)
            log.debug(f'Writing config to {ini_path}...')
            self.parser.write(file)
            self.written = True
            log.info(f'Config saved to {ini_path}')

    def read(self) -> List[ConfigValue]:
        values = []
        self.initialize_parser()
        ini_path = self.resolve_ini_path()
        try:
            with open(ini_path, 'r') as file:
                self.read_existing_config(file, ini_path)
            for section_name, section_proxy in self.parser.items():
                for key, value in section_proxy.items():
                    values.append(ConfigValue(section_name, key, value))
        except FileNotFoundError:
            log.debug(f'No existing config file found at {ini_path}')
        return values

    def delete_section(self, section: str) -> None:
        self.require_parser()
        self.parser.remove_section(section)


class Configurer:

    def __init__(
                self,
                config,
                helper: Helper,
                terms_manager: TermsManager,
                subcommand_definitions: Dict[str, SubcommandDefinition],
                subcommand_definition: Optional[SubcommandDefinition] = None
            ):
        self.config = config
        self.helper = helper
        self.all_config = {}
        self.all_config[config.subcommand] = config
        self.config_values = []
        self.terms_manager = terms_manager
        self.subcommand_definition = subcommand_definition
        self.subcommand_definitions = subcommand_definitions
        self.written = False
        self.config_file_manager = None

    def get_config_file_manager(self) -> ConfigFileManager:
        if self.config_file_manager is None:
            self.config_file_manager = ConfigFileManager(self.config)
        return self.config_file_manager

    def get_config(self, subcommand: str):
        if subcommand not in self.all_config:
            self.all_config[subcommand], _subcommand_definition = load_config(
                        self.subcommand_definitions,
                        self.helper,
                        subcommand
                    )
        return self.all_config[subcommand]

    def supports_option(self, name: str) -> bool:
        if self.subcommand_definition is None:
            return False
        return self.subcommand_definition.accepts_option(name)

    def has_base_config(self) -> bool:
        if self.config.license is None:
            return False
        try:
            ensure_directory_is_writable(self.config.cache_directory)
        except IoException:
            log.warning(
                    f'Cache directory at {self.config.cache_directory} does'
                    'not appear to be writable. Please correct the permissions'
                    ' or specify an alternate path for the cache.'
                )
            return False
        return True

    def _prompt_overwrite(self) -> bool:
        if self.config.has_ini_file():
            overwrite = prompt_yes_no(
                    'An existing configuration file was found at '
                    f'{self.config.ini_path}, do you want to overwrite it?',
                    default=False
                )
            return overwrite
        return True

    def _create_noc1_client(
                self,
                license: Optional[str] = None
            ) -> noc1.Client:
        return noc1.Client(License(license), self.config.noc1_url)

    def _request_free_license(self, terms_accepted: bool = False) -> str:
        client = self._create_noc1_client()
        return client.get_cli_api_key(accept_terms=terms_accepted)

    def _prompt_for_license(self) -> str:
        if self.config.license is not None:
            print(f'Current license: {self.config.license}')
            change_license = prompt_yes_no(
                    'An existing license was found, '
                    'would you like to change it?',
                    default=False
                )
            if not change_license:
                return self.config.license
        request_free = prompt_yes_no(
                'Would you like to automatically request a free Wordfence CLI'
                ' license?',
                default=True
            )
        if not request_free:
            print(f'Please visit {LICENSE_URL} to obtain a license key.')

        def _validate_license(license: str) -> str:
            client = self._create_noc1_client(license)
            try:
                if not client.ping_api_key():
                    raise InvalidInputException('Invalid license')
            except ApiException as e:
                if e.public_message is not None:
                    raise InvalidInputException(
                            f'Invalid license: {e.public_message}'
                        )
                else:
                    raise InvalidInputException(
                            'License validation failed. Please try again.'
                        )
            return license

        if request_free:
            terms_accepted = prompt_yes_no(
                    'Your access to and use of Wordfence CLI Free edition is '
                    'subject to the Wordfence CLI License Terms and '
                    f'Conditions set forth at {TERMS_URL}. By entering "y" '
                    'and selecting Enter, you agree that you have read and '
                    'accept the Wordfence CLI License Terms and Conditions.',
                    default=False
                )
            if terms_accepted:
                license = self._request_free_license(terms_accepted)
                self.terms_manager.record_acceptance(False)
                print(
                        'Free Wordfence CLI license obtained successfully: '
                        f'{license}'
                    )
                return license
            else:
                print(
                        'A license cannot be obtained automatically without'
                        ' agreeing to the Wordfence CLI License Terms and '
                        'Conditions.'
                    )

        license = prompt(
                'License',
                self.config.license,
                transformer=_validate_license
            )
        return license

    def _prompt_for_cache_directory(self) -> str:

        def _validate_writable(directory: str) -> None:
            try:
                ensure_directory_is_writable(directory)
            except IoException as e:
                raise InvalidInputException(
                        f'Directory {directory} is not writable'
                    ) from e
            return directory

        directory = prompt(
                'Cache directory',
                self.config.cache_directory,
                transformer=_validate_writable
            )
        return directory

    def _prompt_for_worker_count(self) -> int:
        cpus = cpu_count()
        config = self.get_config('malware-scan')
        processes = prompt_int(
                    f'Number of worker processes ({cpus} CPUs available)',
                    config.workers
                )
        return processes

    def read_config(self) -> List[ConfigValue]:
        manager = self.get_config_file_manager()
        return manager.read()

    def write_config(self) -> None:
        manager = self.get_config_file_manager()
        manager.write(self.config_values)

    def update_config(
                self,
                key: str,
                value: str,
                section: str = 'DEFAULT'
            ) -> None:
        self.config_values.append(
                ConfigValue(section, key, str(value))
            )
        if self.supports_option(key):
            setattr(self.config, key, value)

    def prompt_for_config(self, overwrite: bool = False) -> bool:
        if not overwrite and not self._prompt_overwrite():
            return False
        has_existing_config = self.config.has_ini_file()
        self.update_config(
                'license',
                self._prompt_for_license()
            )
        self.update_config(
                'cache_directory',
                self._prompt_for_cache_directory()
            )
        self.update_config(
                'workers',
                self._prompt_for_worker_count(),
                'MALWARE_SCAN'
            )
        self.write_config()
        if has_existing_config:
            log.info(
                    "The configuration for Wordfence CLI has been "
                    "successfully updated."
                )
        else:
            log.info(
                    "Wordfence CLI has been successfully configured and is "
                    "now ready for use."
                )
        return True

    def convert_legacy_config(self) -> bool:
        values = self.read_config()
        has_legacy_config = False
        for value in values:
            if not value.section == LEGACY_CONFIG_SECTION:
                continue
            if value.key in LEGACY_CONFIG_KEYS:
                setattr(self.config, value.key, value.value)
                has_legacy_config = True
            else:
                self.update_config(
                        value.key,
                        value.value,
                        LEGACY_CONVERSION_SECTION
                    )
        if not has_legacy_config:
            return False
        should_convert = prompt_yes_no(
                'A configuration file for an older version of Wordfence CLI '
                'was detected; would you like to update it now?',
                default=True
            )
        if should_convert:
            self.config_file_manager.delete_section(LEGACY_CONFIG_SECTION)
            self.prompt_for_config(overwrite=True)
        return True

    def prompt_for_missing_config(self) -> bool:
        should_configure = prompt_yes_no(
                'Wordfence CLI cannot be used until it has been configured. '
                'Would you like to configure it now?',
                default=False
            )
        if should_configure:
            self.prompt_for_config()
            return True
        else:
            return False

    def check_config(self) -> bool:
        if self.has_base_config():
            return True
        else:
            if not self.convert_legacy_config():
                self.prompt_for_missing_config()
            return False
