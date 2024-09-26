import json
import re
import base64
from typing import Callable, Optional

from .noc_client import NocClient
from .exceptions import ApiException
from .licensing import License

from ..intel.signatures import CommonString, Signature, SignatureSet, \
    PrecompiledSignatureSet, deserialize_precompiled_signature_set
from ..intel.database_rules import DatabaseRuleSet, JSON_VALIDATOR as \
    DATABASE_RULES_JSON_VALIDATOR, parse_database_rules
from ..util.validation import DictionaryValidator, ListValidator, Validator, \
    OptionalValueValidator
from ..util.platform import Platform

NOC1_BASE_URL = 'https://noc1.wordfence.com/v2.27/'


API_ERROR_PATTERN = re.compile(r'\{.*errorMsg')


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
                callable: Callable[[bool, License], None]
            ) -> None:
        if not hasattr(self, 'terms_update_hooks'):
            self.terms_update_hooks = []
        self.terms_update_hooks.append(callable)

    def _trigger_terms_update_hooks(
                self,
                updated: bool,
                license: License
            ) -> None:
        if not hasattr(self, 'terms_update_hooks'):
            return
        for hook in self.terms_update_hooks:
            hook(updated, license)

    def register_license_update_hook(
                self,
                callable: Callable[[License], None]
            ) -> None:
        if not hasattr(self, 'license_update_hooks'):
            self.license_update_hooks = []
        self.license_update_hooks.append(callable)

    def _trigger_license_update_hooks(self, license: License) -> None:
        if not hasattr(self, 'license_update_hooks'):
            return
        for hook in self.license_update_hooks:
            hook(license)

    def _check_error_message(self, response: dict) -> None:
        if 'errorMsg' in response:
            raise ApiException(
                    'Error message received in response body',
                    response['errorMsg']
                )

    def validate_response(self, response, validator: Validator) -> None:
        if isinstance(response, dict):
            self._check_error_message(response)
            paid = bool('_isPaidKey' in response and response['_isPaidKey'])
            if paid != self.license.paid:
                self.license.paid = paid
                self._trigger_license_update_hooks(self.license)
            terms_updated = '_termsUpdated' in response
            self._trigger_terms_update_hooks(terms_updated, self.license)
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

    def get_precompiled_patterns(
                self,
                platform: str,
                library_version: str,
                library_type: Optional[str] = None,
                database_version: int = PrecompiledSignatureSet.VERSION
            ) -> dict:
        parameters = {
                'platform': platform,
                'library_version': library_version,
                'database_version': database_version
            }
        if library_type is not None:
            parameters['library_type'] = library_type
        response = self.request('get_precompiled_patterns', parameters)
        validator = DictionaryValidator({
                'data': OptionalValueValidator(str)
            })
        self.validate_response(response, validator)
        return response

    def get_precompiled_malware_signatures(
                self,
                platform: Platform,
                library_version: str,
                library_type: Optional[str] = None,
                database_version: int = PrecompiledSignatureSet.VERSION
            ) -> Optional[PrecompiledSignatureSet]:
        response = self.get_precompiled_patterns(
                platform.key,
                library_version,
                library_type,
                database_version
            )
        data = response['data']
        if data is None:
            return None
        data = base64.b64decode(data)
        signature_set = deserialize_precompiled_signature_set(data)
        signature_set.assign_license(self.license)
        if isinstance(signature_set, PrecompiledSignatureSet):
            return signature_set
        raise ApiException(
                'Malformed signature set data received from Wordfence API'
            )

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

    def get_terms(self) -> str:
        response = self.request('get_terms')
        validator = DictionaryValidator({
                'terms': str
            })
        self.validate_response(response, validator)
        return response['terms']

    def request_raw(
                self,
                action: str,
                query: Optional[dict] = None,
                body: Optional[dict] = None
            ) -> bytes:
        response = self.request(
                action,
                query,
                body,
                json=False
            )
        try:
            response_string = response.decode('utf-8')
            if API_ERROR_PATTERN.match(response_string):
                json_data = json.loads(response)
                self._check_error_message(json_data)
        except (UnicodeError, json.JSONDecodeError):
            pass  # If the response isn't valid JSON, then there's no error
        return response

    def get_wp_file_content(
                self,
                type: str,
                path: str,
                coreVersion: str,
                name: Optional[str] = None,
                version: Optional[str] = None
            ) -> str:
        parameters = {
                'cType': type,
                'file': path,
                'v': coreVersion,
            }
        if name is not None:
            parameters['cName'] = name
        if version is not None:
            parameters['cVersion'] = version
        response = self.request_raw(
                'get_wp_file_content',
                body=parameters
            )
        return response

    def get_database_rules(self) -> DatabaseRuleSet:
        response = self.request('get_database_rules')
        validator = DictionaryValidator({
                'rules': DATABASE_RULES_JSON_VALIDATOR
            })
        self.validate_response(response, validator)
        return parse_database_rules(response['rules'], pre_validated=True)
