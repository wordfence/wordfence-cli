import json

from .exceptions import ApiException
from .noc_client import NocClient

from ..intel.signatures import CommonString, Signature, SignatureSet
from ..util.validation import DictionaryValidator, ListValidator, \
        ValidationException

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

    def get_patterns(self, regex_engine: str = None) -> dict:
        base_query = {}
        if regex_engine is not None:
            base_query['regex_engine'] = regex_engine
        patterns = self.request('get_patterns', base_query)
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
        try:
            validator.validate(patterns)
            return patterns
        except ValidationException as exception:
            raise ApiException('Response validation failed') from exception

    def get_malware_signatures(self) -> SignatureSet:
        patterns = self.get_patterns(regex_engine='python')
        common_strings = []
        signatures = {}
        for string in patterns['commonStrings']:
            common_strings.append(CommonString(string))
        for record in patterns['rules']:
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
                    raise index_error  # TODO: How should this be handled
        return SignatureSet(common_strings, signatures)
