from typing import List, Dict

from ...intel.vulnerabilities import ScannableSoftware, Vulnerability
from ..reporting import Report, ReportColumnEnum, ReportFormatEnum, \
        ReportRecord, ReportManager, ReportFormat, ReportColumn, \
        get_config_options, \
        REPORT_FORMAT_CSV, REPORT_FORMAT_TSV, REPORT_FORMAT_NULL_DELIMITED, \
        REPORT_FORMAT_LINE_DELIMITED
from ..config import Config


class VulnScanReportColumn(ReportColumnEnum):
    SOFTWARE_TYPE = 'software_type', lambda record: record.software.type
    SLUG = 'slug', lambda record: record.software.slug
    VERSION = 'version', lambda record: record.software.version
    VULNERABILITY_ID = 'vulnerability_id', \
        lambda record: record.vulnerability.identifier
    LINK = 'link', lambda record: record.vulnerability.get_wordfence_link()


class VulnScanReportFormat(ReportFormatEnum):
    CSV = REPORT_FORMAT_CSV
    TSV = REPORT_FORMAT_TSV
    NULL_DELIMITED = REPORT_FORMAT_NULL_DELIMITED
    LINE_DELIMITED = REPORT_FORMAT_LINE_DELIMITED


class VulnScanReportRecord(ReportRecord):

    def __init__(
                self,
                software: ScannableSoftware,
                vulnerability: Vulnerability
            ):
        self.software = software
        self.vulnerability = vulnerability


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
            VulnScanReportColumn.VULNERABILITY_ID
        ]
    )


class VulnScanReportManager(ReportManager):

    def __init__(
                self,
                config: Config
            ):
        super().__init__(
                formats=VulnScanReportFormat,
                columns=VulnScanReportColumn,
                config=config,
                read_stdin=config.read_stdin,
                input_delimiter=config.path_separator
            )

    def _instantiate_report(
                self,
                format: ReportFormat,
                columns: List[ReportColumn],
                write_headers: bool
            ) -> VulnScanReport:
        return VulnScanReport(
                format,
                columns,
                write_headers
            )
