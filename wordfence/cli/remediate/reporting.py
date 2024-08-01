import os

from typing import List, Optional, Dict
from email.message import EmailMessage
from email.headerregistry import Address

from ...wordpress.remediator import RemediationResult
from ...wordpress.identifier import FileType
from ...util.terminal import Color, escape, RESET
from ..email import Mailer
from ..reporting import ReportColumnEnum, Report, ReportManager, \
        ReportFormatEnum, ReportFormat, ReportColumn, ReportRecord, \
        ReportEmail, BaseHumanReadableWriter, \
        get_config_options, generate_report_email_html, generate_html_table, \
        REPORT_FORMAT_CSV, REPORT_FORMAT_TSV, REPORT_FORMAT_NULL_DELIMITED, \
        REPORT_FORMAT_LINE_DELIMITED
from ..context import CliContext
from ...util.encoding import bytes_to_str


class RemediationReportColumn(ReportColumnEnum):
    PATH = 'path', lambda record: os.fsdecode(record.result.path),
    STATUS = 'status', lambda record: record.get_status(),
    TYPE = 'type', lambda record: record.result.identity.type,
    SITE = 'site', \
        lambda record: os.fsdecode(
                record.result.identity.site.core_path
            ) \
        if record.result.identity.site is not None \
        else None
    TARGET_PATH = 'target_path', \
        lambda record: os.fsdecode(record.result.target_path),
    WORDPRESS_VERSION = 'wordpress_version', \
        lambda record: bytes_to_str(
                record.result.identity.site.get_version()
            ) \
        if record.result.identity.site is not None \
        else None
    EXTENSION_SLUG = 'extension_slug', \
        lambda record: record.result.identity.extension.slug \
        if record.result.identity.extension is not None else None
    EXTENSION_NAME = 'extension_name', \
        lambda record: record.result.identity.extension.get_name() \
        if record.result.identity.extension is not None else None
    EXTENSION_VERSION = 'extension_version', \
        lambda record: bytes_to_str(
                record.result.identity.extension.version
            ) \
        if record.result.identity.extension is not None else None


class HumanReadableWriter(BaseHumanReadableWriter):

    def format_record(self, record) -> str:
        result = record.result
        path_str = os.fsdecode(result.path)
        if result.remediated:
            green = escape(Color.GREEN)
            return f'{green}Successfully remediated {path_str}{RESET}'
        elif not result.known:
            yellow = escape(Color.YELLOW)
            return (
                    f'{yellow}Path at {path_str} is unknown and cannot'
                    f' be remediated{RESET}'
                )
        else:
            red = escape(Color.RED)
            return f'{red}Remediation for {path_str} failed{RESET}'


REPORT_FORMAT_HUMAN = ReportFormat(
        'human',
        lambda stream, columns: HumanReadableWriter(stream),
        allows_headers=False,
        allows_column_customization=False
    )


class RemediationReportFormat(ReportFormatEnum):
    CSV = REPORT_FORMAT_CSV
    TSV = REPORT_FORMAT_TSV
    NULL_DELIMITED = REPORT_FORMAT_NULL_DELIMITED
    LINE_DELIMITED = REPORT_FORMAT_LINE_DELIMITED
    HUMAN = REPORT_FORMAT_HUMAN


class RemediationReportRecord(ReportRecord):

    def __init__(self, result: RemediationResult):
        self.result = result

    def get_status(self) -> str:
        if self.result.remediated:
            return 'remediated'
        if self.result.identity.type == FileType.UNKNOWN:
            return 'unidentified'
        if not self.result.known:
            return 'unrecognized'
        return 'failed'


class RemediationCounts:

    def __init__(self):
        self.total = 0
        self.remediated = 0
        self.known = 0
        self.unknown = 0

    def add(self, result: RemediationResult):
        if result.remediated:
            self.remediated += 1
        if result.identity.type is FileType.UNKNOWN:
            self.unknown += 1
        else:
            self.known += 1
        self.total += 1

    @property
    def unsuccessful(self):
        return self.total - self.remediated


class RemediationReport(Report):

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
        self.only_unremediated = only_unremediated
        self.counts = RemediationCounts()

    def add_result(self, result: RemediationResult):
        self.counts.add(result)
        if self.only_unremediated and result.remediated:
            return
        self.write_record(
                RemediationReportRecord(
                    result
                )
            )

    def generate_email(
                self,
                recipient: Address,
                attachments: Dict[str, str],
                hostname: str
            ) -> EmailMessage:

        plain = 'Remediation Complete\n\n' \
                'Successfully Remediated Files: ' \
                f'{self.counts.remediated}\n\n' \
                f'Total Files Processed: {self.counts.total}\n\n' \

        results = {
                'Remediated': self.counts.remediated,
                'Failed': self.counts.unsuccessful,
                'Unknown Files': self.counts.unknown,
                'Total': self.counts.total
            }

        table = generate_html_table(results)

        document = generate_report_email_html(
                table,
                'Remediation Results',
                hostname
            )

        return ReportEmail(
                recipient=recipient,
                subject=f'Remediation Results for {hostname}',
                plain_content=plain,
                html_content=document.to_html()
            )


class RemediationReportManager(ReportManager):

    def __init__(self, context: CliContext):
        super().__init__(
                formats=RemediationReportFormat,
                columns=RemediationReportColumn,
                context=context,
                read_stdin=context.config.read_stdin,
                input_delimiter=context.config.path_separator,
                binary_input=True
            )
        self.only_unremediated = context.config.output_unremediated

    def _instantiate_report(
                self,
                format: ReportFormat,
                columns: List[ReportColumn],
                email_addresses: List[str],
                mailer: Optional[Mailer],
                write_headers: bool
            ) -> RemediationReport:
        return RemediationReport(
                format,
                columns,
                email_addresses,
                mailer,
                write_headers,
                self.only_unremediated
            )


REMEDIATION_REPORT_CONFIG_OPTIONS = get_config_options(
        RemediationReportFormat,
        RemediationReportColumn,
        default_format='human'
    )
