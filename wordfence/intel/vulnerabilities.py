import re
import os.path
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Union, Set, Callable, Generator

from ..util.versioning import PhpVersion, compare_php_versions
from ..util.url import Url
from ..wordpress.site import WordpressSite
from ..wordpress.extension import Extension
from ..wordpress.plugin import Plugin
from ..wordpress.theme import Theme


VERSION_ANY = '*'


@dataclass
class VersionRange:
    from_version: str
    from_inclusive: bool
    to_version: str
    to_inclusive: bool

    def includes(self, version: Union[PhpVersion, str]) -> bool:
        from_result = compare_php_versions(self.from_version, version)
        if not (self.from_version == VERSION_ANY or
                from_result == -1 or
                (self.from_inclusive and from_result == 0)):
            return False
        to_result = compare_php_versions(self.to_version, version)
        if not (self.to_version == VERSION_ANY or
                to_result == 1 or
                (self.to_inclusive and to_result == 0)):
            return False
        return True


class SoftwareType(str, Enum):
    CORE = 'core'
    PLUGIN = 'plugin'
    THEME = 'theme'

    def __reduce_ex__(self, proto):
        return (SoftwareType, (self.value,))


@dataclass
class ScannableSoftware:
    type: SoftwareType
    slug: str
    version: bytes
    scan_path: Optional[str]

    def get_key(self) -> str:
        return f'{self.type.value}-{self.slug}-{self.version}'


@dataclass
class Software:
    type: SoftwareType
    name: str
    slug: str
    affected_versions: Dict[str, VersionRange] = field(default_factory=dict)
    patched: bool = False
    patched_versions: List[str] = field(default_factory=list)


@dataclass
class Copyright:
    notice: str
    license: str
    license_url: str


@dataclass
class CopyrightInformation:
    message: Optional[str] = None
    copyrights: Dict[str, Copyright] = field(default_factory=dict)


@dataclass
class Vulnerability:
    identifier: str
    title: str
    software: List[Software] = field(default_factory=list)
    informational: bool = False
    references: List[str] = field(default_factory=list)
    published: Optional[str] = None
    copyright_information: Optional[CopyrightInformation] = None

    def get_wordfence_link(self) -> Optional[str]:
        for url in self.references:
            try:
                url_object = Url(url)
                if url_object.get_hostname() == 'www.wordfence.com':
                    url_object.set_query_parameter('source', 'cli-scan')
                    return str(url_object)
            except ValueError:
                continue
        return None

    def get_matched_software(self, scannable: ScannableSoftware) -> Software:
        for software in self.software:
            if software.type != scannable.type \
                    or software.slug != scannable.slug:
                continue
            for affected in software.affected_versions.values():
                if affected.includes(scannable.version):
                    return software


@dataclass
class ScannerVulnerability(Vulnerability):
    pass


@dataclass
class Cwe:
    identifier: int
    name: str
    description: str


@dataclass
class Cvss:
    vector: str
    score: Union[float, int]
    rating: str


@dataclass
class ProductionSoftware(Software):
    remediation: str = ''


@dataclass
class ProductionVulnerability(Vulnerability):
    software: List[ProductionSoftware] = field(default_factory=list)
    description: str = ''
    cwe: Optional[Cwe] = None
    cvss: Optional[Cvss] = None
    cve: Optional[str] = None
    cve_link: Optional[str] = None
    researchers: List[str] = field(default_factory=list)
    updated: Optional[str] = None


SLUG_WORDPRESS = 'wordpress'


class VulnerabilityIndex:

    def __init__(self, vulnerabilities: Dict[str, Vulnerability]):
        self.vulnerabilities = vulnerabilities
        self.id_map = {}
        self.cve_map = {}
        self._initialize_index(vulnerabilities)

    def _add_vulnerability_to_index(
                self,
                vulnerability: Vulnerability
            ) -> None:
        self.id_map[vulnerability.identifier.casefold()] = \
            vulnerability.identifier
        if hasattr(vulnerability, 'cve') and vulnerability.cve is not None:
            self.cve_map[vulnerability.cve.casefold()] = \
                vulnerability.identifier
        for software in vulnerability.software:
            type_index = self.index[software.type]
            if software.slug not in type_index:
                type_index[software.slug] = []
            software_index = type_index[software.slug]
            for version_range in software.affected_versions.values():
                software_index.append(
                        (
                            version_range,
                            vulnerability.identifier
                        )
                    )

    def _initialize_index(self, vulnerabilities: Dict[str, Vulnerability]):
        self.index = {}
        for type in SoftwareType:
            self.index[type] = {}
        for vulnerability in vulnerabilities.values():
            self._add_vulnerability_to_index(vulnerability)

    def get_vulnerabilities(
                self,
                software_type: SoftwareType,
                slug: str,
                version: str
            ) -> Dict[str, Vulnerability]:
        vulnerabilities = {}
        type_index = self.index[software_type]
        if slug in type_index:
            software_index = type_index[slug]
            for version_range, identifier in software_index:
                if version_range.includes(version):
                    vulnerabilities[identifier] = \
                            self.vulnerabilities[identifier]
        return vulnerabilities

    def get_core_vulnerabilties(
                self,
                version: str
            ) -> Dict[str, Vulnerability]:
        return self.get_vulnerabilities(
                SoftwareType.CORE,
                SLUG_WORDPRESS,
                version
            )

    def get_plugin_vulnerabilities(
                self,
                slug: str,
                version: str
            ) -> Dict[str, Vulnerability]:
        return self.get_vulnerabilities(
                SoftwareType.PLUGIN,
                slug,
                version
            )

    def get_theme_vulnerabilities(
                self,
                slug: str,
                version: str
            ) -> Dict[str, Vulnerability]:
        return self.get_vulnerabilities(
                SoftwareType.THEME,
                slug,
                version
            )

    def includes_vulnerability(self, identifier: str) -> bool:
        casefolded = identifier.casefold()
        return casefolded in self.vulnerabilities or casefolded in self.cve_map


CVE_PATTERN = re.compile(r'^CVE-(199\d|20\d{2})-\d{4,}$', re.IGNORECASE)


def is_cve_id(value: str) -> bool:
    return CVE_PATTERN.match(value) is not None


class VulnerabilityFilter:

    def __init__(
                self,
                excluded: Set[str],
                included: Set[str],
                informational: bool = False
            ):
        self.filtered_ids = set(included) | set(excluded)
        self.excluded = self._make_case_insensitive(excluded)
        self.included = self._make_case_insensitive(included)
        self.informational = informational

    def _make_case_insensitive(self, vulnerability_set: Set[str]) -> Set[str]:
        return {identifier.casefold() for identifier in vulnerability_set}

    def _contains_vulnerability(
                self,
                vulnerability_set: Set[str],
                vulnerability: Vulnerability
            ) -> bool:
        if vulnerability.identifier.casefold() in vulnerability_set:
            return True
        if hasattr(vulnerability, 'cve') \
                and vulnerability.cve is not None \
                and vulnerability.cve.casefold() in vulnerability_set:
            return True
        return False

    def allows(self, vulnerability: Vulnerability) -> bool:
        if self._contains_vulnerability(self.excluded, vulnerability):
            return False
        if len(self.included) and \
                not self._contains_vulnerability(self.included, vulnerability):
            return False
        if vulnerability.informational and not self.informational:
            return False
        return True

    def filter(
                self,
                vulnerabilities: Dict[str, Vulnerability]
            ) -> Dict[str, Vulnerability]:
        return {
                identifier: vulnerability for identifier, vulnerability
                in vulnerabilities.items() if self.allows(vulnerability)
            }

    def get_invalid_ids(
                self,
                index: VulnerabilityIndex
            ) -> Generator[None, None, str]:
        for identifier in self.filtered_ids:
            if not index.includes_vulnerability(identifier):
                yield identifier


DEFAULT_FILTER = VulnerabilityFilter(
        excluded={},
        included={},
        informational=False
    )


class AlreadyScannedException(Exception):
    pass


class VulnerabilityScanner:

    def __init__(
                self,
                index: VulnerabilityIndex,
                filter: VulnerabilityFilter = DEFAULT_FILTER
            ):
        self.index = index
        self.filter = filter
        self.vulnerabilities = {}
        self.affected = {}
        self.callbacks = []
        self.scan_paths = set()

    def register_result_callback(
                    self,
                    callback: Callable[
                        [ScannableSoftware, Dict[str, Vulnerability]],
                        None
                    ]
                ) -> None:
        self.callbacks.append(callback)

    def _trigger_callbacks(
                self,
                software: ScannableSoftware,
                vulnerabilities: Dict[str, Vulnerability]
            ) -> None:
        for callback in self.callbacks:
            callback(software, vulnerabilities)

    def add_scan_path(self, path: str) -> None:
        realpath = os.path.realpath(path)
        if realpath in self.scan_paths:
            raise AlreadyScannedException(f'{path} has already been scanned')
        self.scan_paths.add(realpath)

    def scan(self, software: ScannableSoftware) -> Dict[str, Vulnerability]:
        vulnerabilities = self.index.get_vulnerabilities(
                software.type,
                software.slug,
                software.version
            )
        vulnerabilities = self.filter.filter(vulnerabilities)
        self._trigger_callbacks(software, vulnerabilities)
        self.vulnerabilities.update(vulnerabilities)
        for identifier in vulnerabilities:
            if identifier not in self.affected:
                self.affected[identifier] = []
            self.affected[identifier].append(software)
        return vulnerabilities

    def scan_core(
                self,
                version: bytes,
                scan_path: Optional[str]
            ) -> Dict[str, Vulnerability]:
        return self.scan(
                ScannableSoftware(
                    type=SoftwareType.CORE,
                    slug=SLUG_WORDPRESS,
                    version=version,
                    scan_path=scan_path
                )
            )

    def scan_site(
                self,
                site: WordpressSite,
                scan_path: Optional[str] = None
            ) -> Dict[str, Vulnerability]:
        return self.scan_core(site.get_version(), scan_path)

    def scan_extension(
                self,
                extension: Extension,
                type: SoftwareType,
                scan_path: Optional[str] = None
            ) -> Dict[str, Vulnerability]:
        return self.scan(
                ScannableSoftware(
                    type=type,
                    slug=extension.slug,
                    version=extension.version,
                    scan_path=scan_path
                )
            )

    def scan_plugin(
                self,
                plugin: Plugin,
                scan_path: Optional[str] = None
            ) -> Dict[str, Vulnerability]:
        return self.scan_extension(plugin, SoftwareType.PLUGIN, scan_path)

    def scan_theme(
                self,
                theme: Theme,
                scan_path: Optional[str] = None
            ) -> Dict[str, Vulnerability]:
        return self.scan_extension(theme, SoftwareType.THEME, scan_path)

    def get_vulnerability_count(self) -> int:
        return len(self.vulnerabilities)

    def get_affected_count(self) -> int:
        affected = set()
        for group in self.affected.values():
            for software in group:
                affected.add(software.get_key())
        return len(affected)

    def get_total_count(self) -> int:
        count = 0
        for group in self.affected.values():
            count += len(group)
        return count
