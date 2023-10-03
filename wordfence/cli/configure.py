from configparser import ConfigParser, DuplicateSectionError
from multiprocessing import cpu_count
from typing import Optional

from wordfence.util.input import prompt, prompt_yes_no, prompt_int, \
        InvalidInputException
from wordfence.util.io import ensure_directory_is_writable, \
        ensure_file_is_writable, resolve_path, IoException
from wordfence.api import noc1
from wordfence.api.licensing import License, LICENSE_URL
from wordfence.api.exceptions import ApiException
from wordfence.logging import log
from .subcommands import SubcommandDefinition
from .terms import TERMS_URL, TermsManager


CONFIG_SECTION_DEFAULT = 'DEFAULT'


class Configurer:

    def __init__(
                self,
                config,
                terms_manager: TermsManager,
                subcommand_definition: Optional[SubcommandDefinition] = None
            ):
        self.config = config
        self.terms_manager = terms_manager
        self.subcommand_definition = subcommand_definition
        self.written = False

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
                    'You must accept the Wordfence CLI License Terms and '
                    f'Conditions as defined at {TERMS_URL} in order to '
                    'request a free license. Do you accept these terms?',
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
        processes = prompt_int(
                    f'Number of worker processes ({cpus} CPUs available)',
                    self.config.workers
                )
        return processes

    def get_config_section(self) -> str:
        if self.subcommand_definition is None:
            return 'DEFAULT'
        return self.subcommand_definition.config_section

    def write_config(self) -> None:
        # TODO: What if the INI file changes after the config is loaded?
        config_parser = ConfigParser()
        ini_path = self.config.ini_path if self.config.has_ini_file() \
            else self.config.configuration
        ini_path = resolve_path(ini_path)
        ensure_file_is_writable(ini_path)
        open_mode = 'r' if self.config.has_ini_file() else 'w'
        with open(ini_path, open_mode + '+') as file:
            if self.config.has_ini_file():
                try:
                    config_parser.read_file(file)
                except BaseException:
                    log.warning(
                            'Failed to read existing config file at '
                            f'{ini_path}. existing data will be truncated.'
                        )

            section = self.get_config_section()

            def set_config(key: str, value: str) -> None:
                config_parser.set(section, key, value)

            try:
                if section != CONFIG_SECTION_DEFAULT:
                    config_parser.add_section(section)
            except DuplicateSectionError:
                pass
            set_config('license', self.config.license)
            set_config('cache_directory', self.config.cache_directory)
            if self.supports_option('workers'):
                set_config('workers', str(self.config.workers))
            file.truncate(0)
            file.seek(0)
            log.info(f'Writing config to {ini_path}...')
            config_parser.write(file)
            self.written = True
            log.info('Config updated')

    def prompt_for_config(self) -> None:
        if not self._prompt_overwrite():
            return
        self.config.license = self._prompt_for_license()
        self.config.cache_directory = self._prompt_for_cache_directory()
        if self.supports_option('workers'):
            self.config.workers = self._prompt_for_worker_count()
        self.write_config()

    def check_config(self) -> None:
        if self.config.configure is False:
            return
        if self.config.configure or not self.has_base_config():
            self.prompt_for_config()
