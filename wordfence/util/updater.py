import requests
from packaging import version
from wordfence.util import caching
from wordfence.util.caching import NoCachedValueException
from wordfence.version import __version__

API = 'https://api.github.com/repos/wordfence/wordfence-cli/releases/latest'


class Version:

    @staticmethod
    def get_latest() -> str | None:
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
            latest_version = caching.Cache.get(
                cache,
                'latest_version',
                86400  # Latest version is valid for 24 hours
            )
        except NoCachedValueException:
            latest_version = Version.get_latest()
            if latest_version is None:
                print('Unable to fetch the latest version. '
                      'The version you are using may be out of date!')
                return
            else:
                caching.Cache.put(cache, 'latest_version', latest_version)

        if version.parse(__version__) < version.parse(latest_version):
            print('A newer version of the Wordfence CLI is available! '
                  'Updating to ' + latest_version + ' is recommended.')
