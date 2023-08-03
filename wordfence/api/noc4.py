from .noc_client import NocClient

NOC4_BASE_URL = 'https://noc4.wordfence.com/v1.11/'


class Client(NocClient):

    def get_default_base_url(self) -> str:
        return NOC4_BASE_URL

    def build_query(self, action: str, base_query: dict = None) -> dict:
        query = super().build_query(action, base_query)
        # TODO: How should site parameters be handled for CLI requests
        query['s'] = 'http://www.example.com'
        query['h'] = 'http://www.example.com'
        return query
