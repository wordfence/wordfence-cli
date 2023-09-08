from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Union


@dataclass
class VersionRange:
    from_version: str
    from_inclusive: bool
    to_version: str
    to_inclusive: bool


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
