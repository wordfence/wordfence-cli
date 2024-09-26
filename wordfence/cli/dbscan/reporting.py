import json
from typing import List, Optional, Dict

from wordfence.databasescanning.scanner import DatabaseScanResult
from ..reporting import ReportManager, ReportColumnEnum, ReportFormatEnum, \
    ReportRecord, Report, ReportFormat, ReportColumn, ReportEmail, \
    get_config_options, generate_html_table, generate_report_email_html, \
    REPORT_FORMAT_CSV, REPORT_FORMAT_TSV, REPORT_FORMAT_NULL_DELIMITED, \
    REPORT_FORMAT_LINE_DELIMITED
from ..context import CliContext
from ..email import Mailer


class DatabaseScanReportColumn(ReportColumnEnum):
    TABLE = 'table', lambda record: record.result.table
    RULE_ID = 'rule_id', lambda record: record.result.rule.identifier
    RULE_DESCRIPTION = 'rule_description', \
        lambda record: record.result.rule.description
    # TODO: Ensure rows can be safely represented as JSON
    ROW = 'row', lambda record: json.dumps(record.result.row)


class DatabaseScanReportFormat(ReportFormatEnum):
    CSV = REPORT_FORMAT_CSV
    TSV = REPORT_FORMAT_TSV
    NULL_DELIMITED = REPORT_FORMAT_NULL_DELIMITED
    LINE_DELIMITED = REPORT_FORMAT_LINE_DELIMITED


class DatabaseScanReportRecord(ReportRecord):

    def __init__(self, result: DatabaseScanResult):
        self.result = result


class DatabaseScanReport(Report):

    def __init__(
                self,
                format: ReportFormat,
                columns: List[ReportColumn],
                email_addresses: List[str],
                mailer: Optional[Mailer],
                write_headers: bool = False,
                only_unremediated: bool = False
            ):
        super().__init__(
                format,
                columns,
                email_addresses,
                mailer,
                write_headers
            )
        self.result_count = 0
        self.database_count = 0

    def add_result(self, result: DatabaseScanResult):
        self.result_count += 1
        self.write_record(
                DatabaseScanReportRecord(result)
            )

    def generate_email(
                self,
                recipient: str,
                attachments: Dict[str, str],
                hostname: str
            ) -> ReportEmail:
        plain = (
                'Database Scan Complete\n\n'
                f'Scanned Databases: {self.database_count}\n\n'
                f'Results Found: {self.result_count}\n\n'
            )

        results = {
                'Scanned Databases': self.database_count,
                'Results Found': self.result_count
            }

        table = generate_html_table(results)

        document = generate_report_email_html(
                table,
                'Database Scan Results',
                hostname
            )

        return ReportEmail(
                recipient=recipient,
                subject=f'Database Scan Results for {hostname}',
                plain_content=plain,
                html_content=document.to_html()
            )


class DatabaseScanReportManager(ReportManager):

    def __init__(self, context: CliContext):
        super().__init__(
                formats=DatabaseScanReportFormat,
                columns=DatabaseScanReportColumn,
                context=context,
                read_stdin=context.config.read_stdin,
                input_delimiter=context.config.path_separator,
                binary_input=True
            )

    def _instantiate_report(
                self,
                format: ReportFormat,
                columns: List[ReportColumn],
                email_addresses: List[str],
                mailer: Optional[Mailer],
                write_headers: bool
            ) -> Report:
        return DatabaseScanReport(
                format,
                columns,
                email_addresses,
                mailer,
                write_headers
            )


DATABASE_SCAN_REPORT_CONFIG_OPTIONS = get_config_options(
        DatabaseScanReportFormat,
        DatabaseScanReportColumn,
        default_format='csv'
    )
