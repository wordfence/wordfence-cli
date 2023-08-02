import requests
from packaging import version
from wordfence.version import __version__

API = 'https://api.github.com/repos/wordfence/wordfence-cli/releases/latest'


class Updater:

    @staticmethod
    def get_latest_version() -> str | None:
        try:
            response = requests.get(API).json()
            if 'tag_name' in response.keys():
                return response['tag_name']
            else:
                return None
        except requests.exceptions.RequestException:
            return None

    @staticmethod
    def check_version():
        latest_version = Updater.get_latest_version()
        if latest_version is None:
            print('Unable to fetch the latest version. '
                  'The version you are using might be out of date!')
        else:
            if version.parse(__version__) < version.parse(latest_version):
                print('A newer version of the Wordfence CLI is available! '
                      'Updating to ' + latest_version + ' is recommended.')
