import requests
import time
from packaging import version
from typing import Optional

from . import caching
from .caching import NoCachedValueException
from ..version import __version__
from ..logging import log

API = 'https://api.github.com/repos/wordfence/wordfence-cli/releases/latest'


class Version:

    @staticmethod
    def get_latest() -> Optional[str]:
        try:
            response = requests.get(API).json()
            if 'tag_name' in response.keys():
                return response['tag_name']
            else:
                return None
        except requests.exceptions.RequestException:
            return None

    @staticmethod
    def check(cache: caching.Cache):
        try:
            caching.Cache.get(cache, 'last_update_check', 86400)
        except NoCachedValueException:
            caching.Cache.put(cache, 'last_update_check', int(time.time()))
            latest_version = Version.get_latest()
            if latest_version is None:
                log.error('Unable to fetch the latest version. '
                          'The version you are using may be out of date!')
                return
            if version.parse(__version__) < version.parse(latest_version):
                log.warning(
                    'A newer version of the Wordfence CLI is available! '
                    'Updating to ' + latest_version + ' is recommended.')
