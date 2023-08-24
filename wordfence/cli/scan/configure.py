import os
from configparser import ConfigParser, DuplicateSectionError
from multiprocessing import cpu_count

from wordfence.util.input import prompt, prompt_yes_no, prompt_int, \
        InvalidInputException
from wordfence.util.io import ensure_directory_is_writable, resolve_path, \
        IoException
from wordfence.api import noc1
from wordfence.api.licensing import License, LICENSE_URL
from wordfence.api.exceptions import ApiException
from wordfence.logging import log
from ..config.defaults import INI_DEFAULT_PATH


class Configurer:

    def __init__(self, config):
        self.config = config

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

    def _prompt_for_license(self) -> str:
        if self.config.license is None:
            print(f'Please visit {LICENSE_URL} to obtain a license key.')
        else:
            print(f'Current license: {self.config.license}')

        def _validate_license(license: str) -> str:
            client = noc1.Client(License(license), self.config.noc1_url)
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

    def write_config(self) -> None:
        # TODO: What if the INI file changes after the config is loaded?
        config_parser = ConfigParser()
        ini_path = self.config.ini_path if self.config.has_ini_file() \
            else INI_DEFAULT_PATH
        ini_path = resolve_path(ini_path)
        ensure_directory_is_writable(os.path.dirname(ini_path))
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

            def set_config(key: str, value: str) -> None:
                config_parser.set('SCAN', key, value)

            try:
                config_parser.add_section('SCAN')
            except DuplicateSectionError:
                pass
            set_config('license', self.config.license)
            set_config('cache_directory', self.config.cache_directory)
            set_config('workers', str(self.config.workers))
            file.truncate(0)
            file.seek(0)
            log.info('Writing config...')
            config_parser.write(file)
            log.info('Config updated')

    def prompt_for_config(self) -> None:
        if not self._prompt_overwrite():
            return
        self.config.license = self._prompt_for_license()
        self.config.cache_directory = self._prompt_for_cache_directory()
        self.config.workers = self._prompt_for_worker_count()
        self.write_config()

    def check_config(self) -> None:
        if self.config.configure is False:
            return
        if self.config.configure or not self.has_base_config():
            self.prompt_for_config()
