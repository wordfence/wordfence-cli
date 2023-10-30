import json
from typing import Callable

from .noc_client import NocClient
from .exceptions import ApiException

from ..intel.signatures import CommonString, Signature, SignatureSet
from ..util.validation import DictionaryValidator, ListValidator, Validator

NOC1_BASE_URL = 'https://noc1.wordfence.com/v2.27/'


class Client(NocClient):

    def get_default_base_url(self) -> str:
        return NOC1_BASE_URL

    def _generate_site_stats(self) -> str:
        return json.dumps({})

    def build_query(self, action: str, base_query: dict = None) -> dict:
        query = super().build_query(action, base_query)
        query['s'] = self._generate_site_stats()
        return query

    def register_terms_update_hook(
                self,
                callable: Callable[[bool], None]
            ) -> None:
        if not hasattr(self, 'terms_update_hooks'):
            self.terms_update_hooks = []
        self.terms_update_hooks.append(callable)

    def _trigger_terms_update_hooks(self, paid: bool = False) -> None:
        if not hasattr(self, 'terms_update_hooks'):
            return
        for hook in self.terms_update_hooks:
            hook(paid)

    def validate_response(self, response, validator: Validator) -> None:
        if isinstance(response, dict):
            if 'errorMsg' in response:
                raise ApiException(
                        'Error message received in response body',
                        response['errorMsg']
                    )
            if '_termsUpdated' in response:
                paid = '_isPaidKey' in response and response['_isPaidKey']
                self._trigger_terms_update_hooks(paid)
        return super().validate_response(response, validator)

    def process_simple_request(self, action: str) -> bool:
        response = self.request(action)
        validator = DictionaryValidator({
                'ok': int
            })
        self.validate_response(response, validator)
        return bool(response['ok'])

    def get_patterns(self) -> dict:
        patterns = self.request('get_patterns')
        validator = DictionaryValidator({
            'badstrings': ListValidator(str),
            'commonStrings': ListValidator(str),
            'rules': ListValidator(ListValidator({
                0: int,
                1: int,
                2: str,
                3: str,
                4: str,
                5: int,
                6: str,
                7: str,
                8: ListValidator(int)
            })),
            'signatureUpdateTime': int,
            'word1': str,
            'word2': str,
            'word3': str
        })
        self.validate_response(patterns, validator)
        return patterns

    def get_malware_signatures(self) -> SignatureSet:
        patterns = self.get_patterns()
        common_strings = []
        signatures = {}
        for string in patterns['commonStrings']:
            common_strings.append(CommonString(string))
        for record in patterns['rules']:
            if record[5] != 0:
                continue
            signature_id = record[0]
            signatures[signature_id] = Signature(
                signature_id,
                record[2],
                record[7],
                record[3],
                record[8]
            )
            for index in record[8]:
                try:
                    common_strings[index].signature_ids.append(signature_id)
                except IndexError as index_error:
                    raise ApiException(
                            'Response data contains malformed common string '
                            'association'
                        ) from index_error
        return SignatureSet(common_strings, signatures, self.license)

    def ping_api_key(self) -> bool:
        return self.process_simple_request('ping_api_key')

    def get_cli_api_key(self, accept_terms: bool = False) -> str:
        response = self.request(
                'get_cli_api_key',
                {'accept_terms': int(accept_terms)}
            )
        validator = DictionaryValidator({
                'apiKey': str
            })
        self.validate_response(response, validator)
        return response['apiKey']

    def record_toupp(self) -> bool:
        success = self.process_simple_request('record_toupp')
        if success:
            self.terms_updated = False
        return success
