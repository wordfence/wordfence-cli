import sys
from typing import Optional, Any, Callable, Set, Union

from ..version import __version__, __version_name__
from ..util import pcre, vectorscan
from ..util.text import yes_no
from ..api import noc1, intelligence
from ..util.caching import Cache, CacheDirectory, RuntimeCache, \
        InvalidCachedValueException, CacheException
from ..util.input import has_terminal_input, has_terminal_output
from ..util.io import resolve_path
from ..api.licensing import License, LicenseRequiredException, \
        LicenseSpecific, to_license
from ..logging import log, LogLevel, LogSettings
from .config.config import Config
from .email import Mailer


class CliContext:

    def __init__(
                self,
                config: Config,
                cacheable_types: Set[str],
                helper,
                allows_color: bool
            ):
        self.config = config
        self.cacheable_types = cacheable_types
        self.set_up_cache(self.config.cache_directory)
        self.helper = helper
        self.allows_color = allows_color
        self._license = None
        self._noc1_client = None
        self._terms_update_hooks = []
        self._license_update_hooks = []
        self._wfi_client = None
        self._mailer = None
        self.configurer = None
        self._log_settings = None

    def get_log_level(self) -> LogLevel:
        if self.config.log_level is not None:
            return LogLevel[self.config.log_level]
        elif self.config.quiet:
            return LogLevel.CRITICAL
        elif self.config.debug:
            return LogLevel.DEBUG
        elif self.config.verbose or (
                    self.config.verbose is None
                    and sys.stdout is not None and sys.stdout.isatty()
                ):
            return LogLevel.VERBOSE
        else:
            return LogLevel.INFO

    def get_log_settings(self) -> LogSettings:
        if self._log_settings is None:
            prefixed = not self.allows_color \
                if self.config.prefix_log_levels is None \
                else self.config.prefix_log_levels
            self._log_settings = LogSettings(
                    level=self.get_log_level(),
                    colored=self.allows_color,
                    prefixed=prefixed
                )
        return self._log_settings

    def initialize_logging(self) -> None:
        settings = self.get_log_settings()
        settings.apply()

    def set_up_cache(self, directory: bytes) -> None:
        cache = self._initialize_cache(directory)
        cache.add_filter(self.filter_cache_entry)
        self.cache = cache

    def _initialize_cache(self, directory: bytes) -> Cache:
        if self.config.cache:
            try:
                return CacheDirectory(
                        resolve_path(directory),
                        self.cacheable_types
                    )
            except CacheException as exception:
                log.warning(
                        'Failed to initialize directory cache: '
                        + str(exception)
                    )
        return RuntimeCache()

    def register_terms_update_hook(
                self,
                callable: Callable[[bool, License], None]
            ) -> None:
        self._terms_update_hooks.append(callable)

    def register_license_update_hook(
                self,
                callable: Callable[[License], None]
            ) -> None:
        self._license_update_hooks.append(callable)

    def get_license(self) -> Optional[License]:
        if self._license is None and self.config.license is not None:
            self._license = License(self.config.license)
        return self._license

    def require_license(self) -> License:
        license = self.get_license()
        if license is None:
            raise LicenseRequiredException()
        return license

    def filter_cache_entry(self, value: Any) -> Any:
        if isinstance(value, LicenseSpecific):
            if not value.is_compatible_with_license(self.require_license()):
                raise InvalidCachedValueException(
                        'Incompatible license'
                    )
        return value

    def create_noc1_client(
                self,
                license: Optional[Union[License, str]] = None,
                use_hooks: bool = True
            ) -> noc1.Client:
        license = to_license(license)
        client = noc1.Client(
                license,
                self.config.noc1_url
            )
        if use_hooks:
            for hook in self._terms_update_hooks:
                client.register_terms_update_hook(hook)
            for hook in self._license_update_hooks:
                client.register_license_update_hook(hook)
        return client

    def get_noc1_client(self) -> noc1.Client:
        if self._noc1_client is None:
            self._noc1_client = self.create_noc1_client(
                    self.require_license(),
                    use_hooks=True
                )
        return self._noc1_client

    def get_wfi_client(self) -> intelligence.Client:
        if self._wfi_client is None:
            self._wfi_client = intelligence.Client(
                    self.config.wfi_url
                )
        return self._wfi_client

    def get_mailer(self) -> Mailer:
        if self._mailer is None:
            self._mailer = Mailer(self.config)
        return self._mailer

    def has_pcre(self) -> bool:
        return pcre.AVAILABLE

    def has_vectorscan(self) -> bool:
        return vectorscan.AVAILABLE

    def display_version(self) -> None:
        if __version_name__ is None:
            name_suffix = ''
        else:
            name_suffix = f' "{__version_name__}"'
        print(f"Wordfence CLI {__version__}{name_suffix}")
        has_pcre = self.has_pcre()
        pcre_support_text = yes_no(has_pcre)
        if has_pcre:
            jit_support_text = yes_no(pcre.HAS_JIT_SUPPORT)
            pcre_support_text += (
                    f" - PCRE Version: {pcre.VERSION}"
                    f" (JIT Supported: {jit_support_text})"
                )
        print(f'PCRE Supported: {pcre_support_text}')
        has_vectorscan = self.has_vectorscan()
        vectorscan_support_text = yes_no(has_vectorscan)
        if has_vectorscan:
            vectorscan_support_text += (
                    f' - Version: {vectorscan.VERSION} (API Version: '
                    f'{vectorscan.API_VERSION})'
                )
        print(f'Vectorscan Supported: {vectorscan_support_text}')

    def has_terminal_output(self) -> bool:
        return has_terminal_output()

    def has_terminal_input(self) -> bool:
        return has_terminal_input()

    def requires_input(self, option: Optional[bool]) -> bool:
        return (
                option is True or
                (option is None and self.has_terminal_input())
            )

    def clean_up(self) -> None:
        if self._mailer is not None:
            self._mailer.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb) -> None:
        self.clean_up()
