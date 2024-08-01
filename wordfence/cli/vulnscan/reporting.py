import os

from typing import List, Dict, Callable, Any, Optional
from email.message import EmailMessage
from email.headerregistry import Address

from ...intel.vulnerabilities import ScannableSoftware, Vulnerability, \
        Software, ProductionVulnerability
from ...api.intelligence import VulnerabilityFeedVariant
from ...util.terminal import Color, escape, RESET
from ...util.html import Tag
from ...util.versioning import version_to_str
from ..reporting import Report, ReportColumnEnum, ReportFormatEnum, \
        ReportRecord, ReportManager, ReportFormat, ReportColumn, \
        BaseHumanReadableWriter, ReportEmail, get_config_options, \
        generate_report_email_html, generate_html_table, \
        REPORT_FORMAT_CSV, REPORT_FORMAT_TSV, REPORT_FORMAT_NULL_DELIMITED, \
        REPORT_FORMAT_LINE_DELIMITED
from ..context import CliContext
from ..email import Mailer


class VulnScanReportColumn(ReportColumnEnum):
    SOFTWARE_TYPE = 'software_type', lambda record: record.software.type.value
    SLUG = 'slug', lambda record: record.software.slug
    VERSION = 'version', lambda record: version_to_str(record.software.version)
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
    SCANNED_PATH = 'scanned_path', lambda record: os.fsdecode(
            record.software.scan_path
        )

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


class HumanReadableWriter(BaseHumanReadableWriter):

    def get_severity_color(self, severity: str) -> str:
        if severity == 'none' or severity == 'low':
            return escape(color=Color.WHITE, bold=True)
        if severity == 'high' or severity == 'critical':
            return escape(color=Color.RED, bold=True)
        return escape(color=Color.YELLOW, bold=True)

    def format_record(self, record) -> str:
        vuln = record.vulnerability
        sw = record.software
        sw_version = version_to_str(sw.version)
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
        if vuln.informational:
            bold_white = escape(color=Color.WHITE, bold=True)
            info_message = f'{bold_white}informational{yellow} '
            if len(severity_message) == 0:
                info_message = ' ' + info_message
        else:
            info_message = ''
        return (
            f'{yellow}Found {severity_message}{info_message}vulnerability '
            f'{vuln.title} in {sw.slug}({sw_version})\n'
            f'{white}Details: {blue}{link}{RESET}'
            )


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
                email_addresses: List[str],
                mailer: Optional[Mailer],
                write_headers: bool = False
            ):
        super().__init__(
                format=format,
                columns=columns,
                email_addresses=email_addresses,
                mailer=mailer,
                write_headers=write_headers
            )
        self.scanner = None

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

    def generate_email(
                self,
                recipient: Address,
                attachments: Dict[str, str],
                hostname: str
            ) -> EmailMessage:

        unique_count = self.scanner.get_vulnerability_count()
        total_count = self.scanner.get_total_count()

        base_message = 'Vulnerabilities were found by Wordfence CLI during ' \
                       'a scan.'

        plain = f'{base_message}\n\n' \
                f'Unique Vulnerabilities: {unique_count}\n' \
                f'Total Vulnerabilities: {total_count}\n'

        content = Tag('div')

        content.append(Tag('p').append(base_message))

        results = {
                'Unique Vulnerabilities': unique_count,
                'Total Vulnerabilities': total_count
            }
        table = generate_html_table(results)
        content.append(table)

        document = generate_report_email_html(
                content,
                'Vulnerability Scan Results',
                hostname
            )

        return ReportEmail(
                recipient=recipient,
                subject=f'Vulnerability Scan Results for {hostname}',
                plain_content=plain,
                html_content=document.to_html()
            )


VULN_SCAN_REPORT_CONFIG_OPTIONS = get_config_options(
        VulnScanReportFormat,
        VulnScanReportColumn,
        default_format='human'
    )


class VulnScanReportManager(ReportManager):

    def __init__(
                self,
                context: CliContext,
                feed_variant: VulnerabilityFeedVariant
            ):
        super().__init__(
                formats=VulnScanReportFormat,
                columns=VulnScanReportColumn,
                context=context,
                read_stdin=context.config.read_stdin,
                input_delimiter=context.config.path_separator,
                binary_input=True
            )
        self.feed_variant = feed_variant

    def _instantiate_report(
                self,
                format: ReportFormat,
                columns: List[ReportColumn],
                email_addresses: List[str],
                mailer: Optional[Mailer],
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
                email_addresses,
                mailer,
                write_headers
            )
