from urllib.parse import urlparse, urlunparse, parse_qs, urlencode


class Url:

    def __init__(self, url: str):
        self._parts = urlparse(url)._asdict()

    def get_hostname(self) -> str:
        return self._parts['netloc']

    def get_query(self) -> str:
        return self._parts['query']

    def set_query(self, query: str) -> None:
        self._parts['query'] = query

    def set_query_parameter(self, key, value) -> None:
        parameters = parse_qs(self.get_query())
        parameters[key] = value
        self.set_query(urlencode(parameters, doseq=True))

    def __str__(self) -> str:
        return urlunparse(self._parts.values())
