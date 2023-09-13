from typing import Optional, Any

from ..util.caching import Cache, InvalidCachedValueException
from ..api.licensing import License, LicenseRequiredException, LicenseSpecific
from .config.config import Config


class CliContext:

    def __init__(self, config: Config, cache: Cache):
        self.config = config
        cache.add_filter(self.filter_cache_entry)
        self.cache = cache
        self._license = None

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
