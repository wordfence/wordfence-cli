import sys
from typing import Optional, Any

from ..version import __version__, __version_name__
from ..util import pcre
from ..api import noc1, intelligence
from ..util.caching import Cache, InvalidCachedValueException
from ..api.licensing import License, LicenseRequiredException, LicenseSpecific
from .config.config import Config


class CliContext:

    def __init__(
                self,
                config: Config,
                cache: Cache,
                helper,
                allows_color: bool
            ):
        self.config = config
        cache.add_filter(self.filter_cache_entry)
        self.cache = cache
        self.helper = helper
        self.allows_color = allows_color
        self._license = None
        self._noc1_client = None
        self._terms_update_hooks = []
        self._wfi_client = None
        self.configurer = None

    def register_terms_update_hook(self, callable: [[], None]) -> None:
        self._terms_update_hooks.append(callable)

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

    def get_noc1_client(self) -> noc1.Client:
        if self._noc1_client is None:
            self._noc1_client = noc1.Client(
                    self.require_license(),
                    self.config.noc1_url
                )
            for hook in self._terms_update_hooks:
                self._noc1_client.register_terms_update_hook(hook)
        return self._noc1_client

    def get_wfi_client(self) -> intelligence.Client:
        if self._wfi_client is None:
            self._wfi_client = intelligence.Client(
                    self.config.wfi_url
                )
        return self._wfi_client

    def display_version(self) -> None:
        print(f"Wordfence CLI {__version__} \"{__version_name__}\"")
        jit_support_text = 'Yes' if pcre.HAS_JIT_SUPPORT else 'No'
        print(
                f"PCRE Version: {pcre.VERSION} - "
                f"JIT Supported: {jit_support_text}"
            )

    def has_terminal_output(self) -> bool:
        return sys.stdout is not None \
                and sys.stdout.isatty()

    def has_terminal_input(self) -> bool:
        return sys.stdin is not None \
                and sys.stdin.isatty()
