import requests
from requests.exceptions import RequestException
from enum import Enum
from typing import Callable, Dict, Type, Optional

from .exceptions import ApiException
from ..util.validation import Validator, DictionaryValidator, ListValidator, \
        AllowedValueValidator, OptionalValueValidator, NumberValidator, \
        ValidationException
from ..intel.vulnerabilities import Vulnerability, ScannerVulnerability, \
        ProductionVulnerability, Software, ProductionSoftware, SoftwareType, \
        VersionRange, Cwe, Cvss, CopyrightInformation, Copyright


DEFAULT_BASE_URL = 'https://www.wordfence.com/api/intelligence/v2'
DEFAULT_TIMEOUT = 30


def get_base_vulnerability_feed_validator() -> Validator:
    return DictionaryValidator(
            validator=DictionaryValidator({
                'id': str,
                'title': str,
                'software': ListValidator(DictionaryValidator({
                        'type': AllowedValueValidator({
                                    'core', 'plugin', 'theme'
                                }),
                        'name': str,
                        'slug': str,
                        'affected_versions': DictionaryValidator(
                            validator=DictionaryValidator({
                                'from_version': str,
                                'from_inclusive': bool,
                                'to_version': str,
                                'to_inclusive': bool
                            })),
                        'patched': bool,
                        'patched_versions': ListValidator(str)
                    })),
                'informational': OptionalValueValidator(bool),
                'references': ListValidator(str),
                'published': OptionalValueValidator(str),
                'copyrights': DictionaryValidator(
                        expected={
                            'message': str,
                        },
                        validator=DictionaryValidator({
                            'notice': str,
                            'license': str,
                            'license_url': str
                        }),
                        allow_empty=True
                    )
            }, optional_keys={'informational'})
        )


def get_production_vulnerability_feed_validator() -> Validator:
    validator = get_base_vulnerability_feed_validator()
    validator.validator.add_field('description', str)
    validator.validator.add_field(
            'cwe',
            OptionalValueValidator(DictionaryValidator({
                'id': int,
                'name': str,
                'description': str
            }))
        )
    validator.validator.add_field(
            'cvss',
            OptionalValueValidator(DictionaryValidator({
                'vector': str,
                'score': NumberValidator(),
                'rating': str
            }))
        )
    validator.validator.add_field('cve', OptionalValueValidator(str))
    validator.validator.add_field('cve_link', OptionalValueValidator(str))
    validator.validator.add_field('researchers', ListValidator(str))
    validator.validator.add_field('updated', OptionalValueValidator(str))
    validator.validator.expected['software'].expected.add_field(
            'remediation',
            str
        )
    return validator


class VulnerabilityParser:

    def __init__(
                self,
                type: Type[Vulnerability],
                software_type: Type[Software] = Software
            ):
        self.type = type
        self.software_type = software_type

    def extract_vulnerability_properties(self, record: dict) -> dict:
        properties = {}
        properties['identifier'] = record['id']
        properties['title'] = record['title']
        if 'informational' in record:
            properties['informational'] = record['informational']
        properties['references'] = record['references']
        properties['published'] = record['published']
        return properties

    def parse_version_range(self, record: dict) -> VersionRange:
        return VersionRange(
                from_version=record['from_version'],
                from_inclusive=record['from_inclusive'],
                to_version=record['to_version'],
                to_inclusive=record['to_inclusive']
            )

    def extract_software_properties(self, record: dict) -> dict:
        properties = {}
        properties['type'] = SoftwareType(record['type'])
        properties['name'] = record['name']
        properties['slug'] = record['slug']
        properties['patched'] = record['patched']
        properties['patched_versions'] = record['patched_versions']
        affected_versions = {}
        for key, affected in record['affected_versions'].items():
            range = self.parse_version_range(affected)
            affected_versions[key] = range
        properties['affected_versions'] = affected_versions
        return properties

    def parse_copyright(self, record: dict) -> Copyright:
        return Copyright(
                notice=record['notice'],
                license=record['license'],
                license_url=record['license']
            )

    def parse_copyright_information(self, record: dict) \
            -> Optional[CopyrightInformation]:
        copyrights = record['copyrights']
        if len(copyrights) > 0:
            info = CopyrightInformation()
            if 'message' in copyrights:
                info.message = copyrights['message']
            for key, copyright in copyrights.items():
                if key == 'message':
                    continue
                info.copyrights[key] = self.parse_copyright(copyright)
            return info
        return None

    def parse(self, record: dict) -> Vulnerability:
        vulnerability = self.type(**self.extract_vulnerability_properties(
                record
            ))
        for software in record['software']:
            vulnerability.software.append(
                        self.software_type(**self.extract_software_properties(
                                software
                            ))
                    )
        vulnerability.copyright_information = self.parse_copyright_information(
                record
            )
        return vulnerability


class ScannerVulnerabilityParser(VulnerabilityParser):

    def __init__(self):
        super().__init__(
                type=ScannerVulnerability
            )

    def parse(self, record: dict) -> ScannerVulnerability:
        return super().parse(record)


class ProductionVulnerabilityParser(VulnerabilityParser):

    def __init__(self):
        super().__init__(
                type=ProductionVulnerability,
                software_type=ProductionSoftware
            )

    def extract_vulnerability_properties(self, record: dict) -> dict:
        properties = super().extract_vulnerability_properties(record)
        properties['description'] = record['description']
        properties['cve'] = record['cve']
        properties['cve_link'] = record['cve_link']
        properties['researchers'] = record['researchers']
        properties['updated'] = record['updated']
        return properties

    def extract_software_properties(self, record: dict) -> dict:
        properties = super().extract_software_properties(record)
        properties['remediation'] = record['remediation']
        return properties

    def parse_cwe(self, record: dict) -> Cwe:
        return Cwe(
                identifier=record['id'],
                name=record['name'],
                description=record['description']
            )

    def parse_cvss(self, record: dict) -> Cvss:
        return Cvss(
                vector=record['vector'],
                score=record['score'],
                rating=record['rating']
            )

    def parse(self, record: dict) -> ProductionVulnerability:
        vulnerability = super().parse(record)
        if record['cwe'] is not None:
            vulnerability.cwe = self.parse_cwe(record['cwe'])
        if record['cvss'] is not None:
            vulnerability.cvss = self.parse_cvss(record['cvss'])
        return vulnerability


class VulnerabilityFeedVariant(Enum):
    SCANNER = (
            'scanner',
            get_base_vulnerability_feed_validator,
            ScannerVulnerabilityParser()
        )
    PRODUCTION = (
            'production',
            get_production_vulnerability_feed_validator,
            ProductionVulnerabilityParser()
        )

    def __init__(
                self,
                path: str,
                validator_factory: Callable[[], Validator],
                parser: VulnerabilityParser
            ):
        self.path = path
        self.validator_factory = validator_factory
        self.validator = None
        self.parser = parser

    def get_validator(self) -> Validator:
        if self.validator is None:
            self.validator = self.validator_factory()
        return self.validator

    @classmethod
    def for_path(cls, path):
        for variant in cls:
            if variant.path == path:
                return variant
        raise ValueError(f'Unrecognized vulnerability feed variant: {path}')


class Client:

    def __init__(
                self,
                base_url: Optional[str] = None,
                timeout: int = DEFAULT_TIMEOUT
            ):
        self.base_url = base_url if base_url is not None else DEFAULT_BASE_URL
        self.timeout = timeout

    def _build_url(self, path: str) -> str:
        return self.base_url.rstrip('/') + path

    def fetch_vulnerability_feed(
                self,
                variant: VulnerabilityFeedVariant
            ) -> Dict[str, Vulnerability]:
        url = self._build_url(f'/vulnerabilities/{variant.path}')
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            variant.get_validator().validate(data)
            vulnerabilities = {}
            for key, record in data.items():
                vulnerabilities[key] = (variant.parser.parse(record))
            return vulnerabilities
        except RequestException as e:
            raise ApiException('Wordfence Intelligence API request failed') \
                from e
        except ValidationException as e:
            raise ApiException(
                        'Wordfence Intelligence API response validation failed'
                    ) \
                from e

    def fetch_scanner_vulnerability_feed(
                self
            ) -> Dict[str, ScannerVulnerability]:
        return self.fetch_vulnerability_feed(VulnerabilityFeedVariant.SCANNER)

    def fetch_production_vulnerability_feed(
                self
            ) -> Dict[str, ProductionVulnerability]:
        return self.fetch_vulnerability_feed(
                VulnerabilityFeedVariant.PRODUCTION
            )
