from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Union

from ..util.versioning import PhpVersion, compare_php_versions


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
    references: List[str] = field(default_factory=list)
    published: Optional[str] = None
    copyright_information: Optional[CopyrightInformation] = None


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
        self._initialize_index(vulnerabilities)

    def _add_vulnerability_to_index(
                self,
                vulnerability: Vulnerability
            ) -> None:
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
