from typing import List, Dict, Callable, Any, Optional

from ...intel.vulnerabilities import ScannableSoftware, Vulnerability, \
        Software, ProductionVulnerability
from ...api.intelligence import VulnerabilityFeedVariant
from ...util.terminal import Color, escape, RESET
from ..reporting import Report, ReportColumnEnum, ReportFormatEnum, \
        ReportRecord, ReportManager, ReportFormat, ReportColumn, \
        RowlessWriter, get_config_options, \
        REPORT_FORMAT_CSV, REPORT_FORMAT_TSV, REPORT_FORMAT_NULL_DELIMITED, \
        REPORT_FORMAT_LINE_DELIMITED
from ..config import Config


class VulnScanReportColumn(ReportColumnEnum):
    SOFTWARE_TYPE = 'software_type', lambda record: record.software.type
    SLUG = 'slug', lambda record: record.software.slug
    VERSION = 'version', lambda record: record.software.version
    ID = 'id', \
        lambda record: record.vulnerability.identifier
    TITLE = 'title', lambda record: record.vulnerability.title
    LINK = 'link', lambda record: record.vulnerability.get_wordfence_link()
    DESCRIPTION = 'description', \
        lambda record: record.vulnerability.description, \
        VulnerabilityFeedVariant.PRODUCTION
    CVE = 'cve', lambda record: record.vulnerability.cve, \
        VulnerabilityFeedVariant.PRODUCTION
    CVSS_VECTOR = 'cvss_vector', \
        lambda record: record.vulnerability.cvss.vector, \
        VulnerabilityFeedVariant.PRODUCTION
    CVSS_SCORE = 'cvss_score', \
        lambda record: record.vulnerability.cvss.score, \
        VulnerabilityFeedVariant.PRODUCTION
    CVSS_RATING = 'cvss_rating', \
        lambda record: record.vulnerability.cvss.rating, \
        VulnerabilityFeedVariant.PRODUCTION
    CWE_ID = 'cwe_id', \
        lambda record: record.vulnerability.cwe.identifier, \
        VulnerabilityFeedVariant.PRODUCTION
    CWE_NAME = 'cwe_name', \
        lambda record: record.vulnerability.cwe.name, \
        VulnerabilityFeedVariant.PRODUCTION
    CWE_DESCRIPTION = 'cwe_description', \
        lambda record: record.vulnerability.cwe.description, \
        VulnerabilityFeedVariant.PRODUCTION
    PATCHED = 'patched', \
        lambda record: record.get_matched_software().patched
    REMEDIATION = 'remediation', \
        lambda record: record.get_matched_software().remediation, \
        VulnerabilityFeedVariant.PRODUCTION,
    PUBLISHED = 'published', lambda record: record.vulnerability.published
    UPDATED = 'updated', \
        lambda record: record.vulnerability.updated, \
        VulnerabilityFeedVariant.PRODUCTION

    def __init__(
                self,
                header: str,
                extractor: Callable[[Any], str],
                feed_variant: Optional[VulnerabilityFeedVariant] = None
            ):
        super().__init__(header, extractor)
        self.feed_variant = feed_variant

    def is_compatible(
                self,
                variant: VulnerabilityFeedVariant
            ) -> bool:
        return self.feed_variant is None or \
                variant == self.feed_variant


class HumanReadableWriter(RowlessWriter):

    def get_severity_color(self, severity: str) -> str:
        if severity == 'none' or severity == 'low':
            return escape(color=Color.WHITE, bold=True)
        if severity == 'high' or severity == 'critical':
            return escape(color=Color.RED, bold=True)
        return escape(color=Color.YELLOW, bold=True)

    def format_record(self, record) -> str:
        vuln = record.vulnerability
        sw = record.software
        yellow = escape(color=Color.YELLOW)
        link = vuln.get_wordfence_link()
        blue = escape(color=Color.BLUE)
        white = escape(color=Color.WHITE)
        severity = None
        if isinstance(record.vulnerability, ProductionVulnerability):
            if record.vulnerability.cvss is not None:
                severity = record.vulnerability.cvss.rating
        if severity is None:
            severity_message = ''
        else:
            severity = severity.lower()
            severity_color = self.get_severity_color(severity)
            severity_message = f'{severity_color}{severity}{yellow} severity '
        return (
            f'{yellow}Found {severity_message}vulnerability {vuln.title} in '
            f'{sw.slug}({sw.version})\n'
            f'{white}Details: {blue}{link}{RESET}'
            )

    def write_record(self, record) -> None:
        self._target.write(self.format_record(record))
        self._target.write('\n')


REPORT_FORMAT_HUMAN = ReportFormat(
        'human',
        lambda stream, columns: HumanReadableWriter(stream),
        allows_headers=False,
        allows_column_customization=False
    )


class VulnScanReportFormat(ReportFormatEnum):
    CSV = REPORT_FORMAT_CSV
    TSV = REPORT_FORMAT_TSV
    NULL_DELIMITED = REPORT_FORMAT_NULL_DELIMITED
    LINE_DELIMITED = REPORT_FORMAT_LINE_DELIMITED
    HUMAN = REPORT_FORMAT_HUMAN


class VulnScanReportRecord(ReportRecord):

    def __init__(
                self,
                software: ScannableSoftware,
                vulnerability: Vulnerability
            ):
        self.software = software
        self.vulnerability = vulnerability
        self.matched_software = None

    def get_matched_software(self) -> Software:
        if self.matched_software is None:
            self.matched_software = \
                    self.vulnerability.get_matched_software(self.software)
        return self.matched_software


class VulnScanReport(Report):

    def __init__(
                self,
                format: VulnScanReportFormat,
                columns: List[VulnScanReportColumn],
                write_headers: bool = False
            ):
        super().__init__(
                format=format,
                columns=columns,
                write_headers=write_headers
            )

    def add_result(
                self,
                software: ScannableSoftware,
                vulnerabilities: Dict[str, Vulnerability]
            ) -> None:
        records = []
        for vulnerability in vulnerabilities.values():
            record = VulnScanReportRecord(
                    software,
                    vulnerability
                )
            records.append(record)
        self.write_records(records)


VULN_SCAN_REPORT_CONFIG_OPTIONS = get_config_options(
        VulnScanReportFormat,
        VulnScanReportColumn,
        [
            VulnScanReportColumn.SLUG,
            VulnScanReportColumn.VERSION,
            VulnScanReportColumn.LINK
        ],
        'human'
    )


class VulnScanReportManager(ReportManager):

    def __init__(
                self,
                config: Config,
                feed_variant: VulnerabilityFeedVariant
            ):
        super().__init__(
                formats=VulnScanReportFormat,
                columns=VulnScanReportColumn,
                config=config,
                read_stdin=config.read_stdin,
                input_delimiter=config.path_separator
            )
        self.feed_variant = feed_variant

    def _instantiate_report(
                self,
                format: ReportFormat,
                columns: List[ReportColumn],
                write_headers: bool
            ) -> VulnScanReport:
        for column in columns:
            if not column.is_compatible(self.feed_variant):
                raise ValueError(
                        f'Column {column.header} is not compatible '
                        'with the current feed'
                    )
        return VulnScanReport(
                format,
                columns,
                write_headers
            )
