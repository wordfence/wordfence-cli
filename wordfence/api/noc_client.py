import json
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError

from .license import License
from .exceptions import ApiException

DEFAULT_TIMEOUT = 30


class NocClient:

    def __init__(
                self,
                license: License,
                base_url: str = None,
                timeout: int = DEFAULT_TIMEOUT
            ):
        self.license = license
        self.base_url = base_url
        self.timeout = timeout

    def get_default_base_url(self) -> str:
        raise ApiException('No default base URL is defined')

    def build_query(self, action: str, base_query: dict = None) -> dict:
        if base_query is None:
            query = {}
        else:
            query = base_query.copy()
        query['action'] = action
        query['k'] = self.license.key
        return query

    def request(self, action: str, query: dict = None):
        query = self.build_query(action, query)
        url = self.base_url + '?' + urlencode(query)
        request = Request(url)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data
        except URLError as error:
            raise ApiException('Request failed') from error
