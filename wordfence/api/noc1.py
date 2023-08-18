import json

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

    def validate_response(self, response, validator: Validator) -> None:
        if isinstance(response, dict) and 'errorMsg' in response:
            raise ApiException(
                    'Error message received in response body',
                    response['errorMsg']
                )
        return super().validate_response(response, validator)

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
        response = self.request('ping_api_key')
        validator = DictionaryValidator({
                'ok': int
            })
        self.validate_response(response, validator)
        return bool(response['ok'])
