import requests
from typing import Optional
from urllib.parse import urlencode

from .licensing import License
from .exceptions import ApiException
from .user_agent import get_user_agent
from ..util.validation import Validator, ValidationException

DEFAULT_TIMEOUT = 30


class NocClient:

    def __init__(
                self,
                license: Optional[License] = None,
                base_url: str = None,
                timeout: int = DEFAULT_TIMEOUT
            ):
        self.license = license
        self.base_url = base_url \
            if base_url is not None \
            else self.get_default_base_url()
        self.timeout = timeout

    def get_default_base_url(self) -> str:
        raise ApiException('No default base URL is defined')

    def build_query(self, action: str, base_query: dict = None) -> dict:
        if base_query is None:
            query = {}
        else:
            query = base_query.copy()
        query['action'] = action
        if self.license is not None:
            query['k'] = self.license.key
        query['cli'] = 1
        return query

    def request(
                self,
                action: str,
                query: dict = None,
                raw_query: bool = False
            ):
        if raw_query:
            # Send only the action and license key, e.g.
            # <base_url>?action=<action>&k=<license>
            exact = {'action': action}
            if self.license is not None:
                exact['k'] = self.license.key
            if query:
                exact.update(query)
            query = exact
        else:
            query = self.build_query(action, query)
        url = self.base_url + '?' + urlencode(query)
        headers = {
            'User-Agent': get_user_agent()
        }
        try:
            response = requests.get(
                    url,
                    timeout=self.timeout,
                    headers=headers
                )
            return response.json()
        except Exception as error:
            raise ApiException('Request failed') from error

    def validate_response(self, response, validator: Validator) -> None:
        try:
            validator.validate(response)
        except ValidationException as exception:
            raise ApiException('Response validation failed') from exception
