import csv
import sys
import os
from typing import IO, List, Any, Callable, Iterable, Type, Dict, Optional, \
        Union
from enum import Enum
from contextlib import nullcontext
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.headerregistry import Address
from socket import gethostname

from wordfence.logging import log
from wordfence.util.io import resolve_path
from wordfence.util.html import Document, Tag, Stylesheet, Style, RawHtml, \
        HtmlContent
from .context import CliContext
from .io import IoManager
from .email import Mailer


class ReportingException(Exception):
    pass


class ReportColumn:

    def __init__(
                self,
                header: str,
                extractor: Callable[[Any], str]
            ):
        self.header = header
        self.extractor = extractor

    def extract_value(self, record: Any) -> str:
        return self.extractor(record)


class ReportColumnEnum(ReportColumn, Enum):

    def __init__(
                self,
                header: str,
                extractor: Callable[[Any], str]
            ):
        super().__init__(header, extractor)

    @classmethod
    def get_options(cls) -> List[str]:
        return [column.header for column in cls]

    @classmethod
    def get_options_as_string(cls, delimiter: str = ', ') -> str:
        return ', '.join(cls.get_options())

    @classmethod
    def for_option(cls, header: str) -> ReportColumn:
        for column in cls:
            if column.header == header:
                return column
        raise ValueError(f'Unrecognized report column: {header}')


REPORT_COLUMNS_ALL = 'all'


class ReportWriter:

    def __init__(self, target: IO):
        self._target = target
        self.initialize()

    def initialize(self) -> None:
        pass

    def write_row(self, data: List[str]):
        pass

    def allows_headers(self) -> bool:
        return True

    def allows_column_customization(self) -> bool:
        return True

    def get_max_columns(self) -> Optional[int]:
        return None


class CsvReportWriter(ReportWriter):

    def initialize(self):
        self.writer = csv.writer(self._target, delimiter=self.get_delimiter())

    def get_delimiter(self) -> str:
        return ','

    def write_row(self, data: List[str]) -> None:
        self.writer.writerow(data)


class TsvReportWriter(CsvReportWriter):

    def get_delimiter(self) -> str:
        return '\t'


class SingleColumnWriter(ReportWriter):

    def __init__(self, target: IO, delimiter: str):
        super().__init__(target)
        self.delimiter = delimiter

    def write_row(self, data: List[str]) -> None:
        for index, value in enumerate(data):
            if index > 0:
                break
            if value is None:
                value = ''
            self._target.write(str(value) + self.delimiter)

    def get_max_columns(self) -> Optional[int]:
        return 1


class RowlessWriter(ReportWriter):

    def allows_headers(self) -> bool:
        return False

    def allows_column_customization(self) -> bool:
        return False

    def write_row(self, data: List[str]) -> None:
        pass

    def write_record(self, record) -> None:
        raise NotImplementedError()


class BaseHumanReadableWriter(RowlessWriter):

    def format_record(self, record) -> str:
        raise NotImplementedError()

    def write_record(self, record) -> None:
        self._target.write(self.format_record(record))
        self._target.write('\n')


class ReportFormat:

    def __init__(
                self,
                option: str,
                initializer: Callable[[IO, List[ReportColumn]], ReportWriter],
                allows_headers: bool = True,
                allows_column_customization: bool = True
            ):
        self.option = option
        self.initializer = initializer
        self.allows_headers = allows_headers
        self.allows_column_customization = allows_column_customization

    def initialize_writer(
                self,
                stream: IO,
                columns: List[ReportColumn]
            ) -> ReportWriter:
        return self.initializer(stream, columns)


REPORT_FORMAT_CSV = ReportFormat(
        'csv',
        lambda stream, columns: CsvReportWriter(stream)
    )
REPORT_FORMAT_TSV = ReportFormat(
        'tsv',
        lambda stream, columns: TsvReportWriter(stream)
    )
REPORT_FORMAT_NULL_DELIMITED = ReportFormat(
        'null-delimited',
        lambda stream, columns: SingleColumnWriter(stream, "\0")
    )
REPORT_FORMAT_LINE_DELIMITED = ReportFormat(
        'line-delimited',
        lambda stream, columns: SingleColumnWriter(stream, "\n")
    )


class ReportFormatEnum(Enum):

    @classmethod
    def get_options(cls) -> List[str]:
        return [format.value.option for format in cls]

    @classmethod
    def for_option(cls, option: str):
        for format in cls:
            if format.value.option == option:
                return format
        raise ValueError(f'Unrecognized report format: {option}')


class ReportRecord:
    pass


def generate_html_table(results: Dict[str, Any]) -> Tag:
    table = Tag(
            'table',
            {
                'class': 'results',
                'align': 'center',
            }
        )
    for key, value in results.items():
        table.append(
            Tag('tr')
            .append(Tag('th', {'align': 'left'})
                    .append(key))
            .append(Tag('td', {'align': 'right'})
                    .append(str(value)))
        )
    return table


def generate_report_email_html(
            content: HtmlContent,
            title: str,
            hostname: str
        ) -> Document:
    document = Document()

    styles = Stylesheet()

    styles.add(
            Style(
                'th, td',
                {
                    'padding': '8px'
                }
            ),
            Style(
                'h1.logo',
                {
                    'font-family': 'serif',
                    'font-size': '18px'
                }
            ),
            Style(
                '.cli-green',
                {
                    'color': '#008000'
                }
            ),
            Style(
                '.logo .cli',
                {
                    'font-family': 'sans'
                }
            ),
            Style(
                'h2',
                {
                    'font-size': '16px'
                }
            ),
            Style(
                'table.container td',
                {
                    'text-align': 'center',
                }
            ),
            Style(
                'div.content',
                {
                    'min-width': '600px',
                    'width': '800px',
                    'background-color': '#F0F0F0',
                    'font-size': '12px',
                    'padding': '8px'
                }
            ),
            Style(
                'table.results, table.results td, table.results th',
                {
                    'border': '1px solid black',
                    'border-collapse': 'collapse'
                }
            ),
            Style(
                'table.results tr, table.results, td',
                {
                    'font-size': '12px'
                }
            )
        )

    document.head.append(styles)

    content_section = Tag('div', {'class': 'content'})
    container = Tag(
                    'table',
                    {
                        'class': 'container',
                        'align': 'center',
                        'cellspacing': '0',
                        'cellpadding': '0',
                        'border': '0'
                    }
                ).append(
                    Tag('tr')
                    .append(
                        Tag('td', {'align': 'center'}).append(content_section)
                    )
                )

    header = Tag('div')
    header.append(
            Tag('h1', {'class': 'logo'})
            .append(RawHtml(
                '<span class="cli-green">Word</span>fence '
                '<span class="cli">CLI</span>'))
        )
    header.append(
            Tag('h2')
            .append(title)
            .append(' for ')
            .append(Tag('font', {'face': 'monospace'})
                    .append(hostname))
        )
    content_section.append(header)

    content_section.append(content)

    document.body.append(container)
    return document


class ReportEmail:

    def __init__(
                self,
                recipient: Address,
                subject: str,
                plain_content: str,
                html_content: str
            ):
        self.recipient = recipient
        self.subject = subject
        self.plain_content = plain_content
        self.html_content = html_content

    def to_mime_multipart(self) -> MIMEMultipart:
        message = MIMEMultipart()
        message['Subject'] = self.subject

        content = MIMEMultipart('alternative')

        body_plain = MIMEText(self.plain_content, 'plain')
        content.attach(body_plain)

        body_html = MIMEText(self.html_content, 'html')
        content.attach(body_html)

        message.attach(content)

        return message


class Report:

    def __init__(
                self,
                format: ReportFormat,
                columns: List[ReportColumn],
                email_addresses: List[str],
                mailer: Optional[Mailer],
                write_headers: bool = False
            ):
        self.format = format.value
        self.columns = columns
        self.email_addresses = email_addresses
        self.mailer = mailer
        self.write_headers = write_headers
        self.headers_written = False
        self.writers = []
        self.has_custom_columns = False
        self.files = {}
        self.rows_written = 0

    def add_target(self, stream: IO, filename: Optional[str] = None) -> None:
        if filename is not None:
            self.files[filename] = stream
        writer = self.format.initialize_writer(stream, self.columns)
        if self.write_headers and not writer.allows_headers():
            log.warning(
                    'Headers are not supported when using the '
                    f'{self.format.option} output format'
                )
        if self.has_custom_columns \
                and not writer.allows_column_customization():
            log.warning(
                    'Columns cannot be specified when using the '
                    f'{self.format.option} output format'
                )
        max_columns = writer.get_max_columns()
        if max_columns is not None and len(self.columns) > max_columns:
            log.warning(
                    'Too many output columns requested for specified format '
                    f'(only {max_columns} allowed)'
                )
        self.writers.append(writer)

    def _write_row(self, data: List[str], record: ReportRecord):
        self.rows_written += 1
        for writer in self.writers:
            if isinstance(writer, RowlessWriter):
                writer.write_record(record)
            else:
                writer.write_row(data)

    def _write_headers(self) -> None:
        if self.headers_written or not self.write_headers:
            return
        headers = [column.header for column in self.columns]
        for writer in self.writers:
            if writer.allows_headers():
                writer.write_row(headers)
        self.headers_written = True

    def _format_record(self, record: ReportRecord) -> List[str]:
        row = []
        for column in self.columns:
            row.append(column.extract_value(record))
        return row

    def _write_record(self, record: ReportRecord) -> None:
        self._write_row(self._format_record(record), record)

    def write_records(self, records: Iterable[ReportRecord]) -> None:
        self._write_headers()
        for record in records:
            self._write_record(record)

    def write_record(self, record: ReportRecord) -> None:
        self._write_headers()
        self._write_record(record)

    def has_writers(self) -> bool:
        return len(self.writers) > 0

    def generate_email(
                self,
                recipient: str,
                attachments: Dict[str, str],
                hostname: str
            ) -> ReportEmail:
        raise NotImplementedError(
                'This report does not support email generation'
            )

    def send_emails(self) -> None:
        attachments = {}
        for name, file in self.files.items():
            file.seek(0)
            content = file.read()
            attachments[os.fsdecode(name)] = content
        hostname = gethostname()
        for recipient in self.email_addresses:
            recipient = Address(addr_spec=recipient)
            email = self.generate_email(recipient, attachments, hostname)
            email = email.to_mime_multipart()
            email['To'] = str(recipient)

            for name, content in attachments.items():
                attachment = MIMEApplication(
                        content,
                        Name=name
                    )
                attachment.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=name
                    )
                email.attach(attachment)

            self.mailer.send(email)

    def complete(self) -> None:
        if self.rows_written > 0 and len(self.email_addresses) > 0:
            self.send_emails()


def get_config_options(
            formats: Type[ReportFormatEnum],
            columns: Type[ReportColumnEnum],
            default_columns: Union[List[ReportColumnEnum], str] =
            REPORT_COLUMNS_ALL,
            default_format: str = 'csv'
        ) -> Dict[str, Dict[str, Any]]:
    if not isinstance(default_columns, str):
        default_columns = ','.join(
                [column.header for column in default_columns]
            )
    header_formats = []
    column_formats = []
    for format in formats:
        if format.value.allows_headers:
            header_formats.append(format.value.option)
        if format.value.allows_column_customization:
            column_formats.append(format.value.option)
    header_format_string = ', '.join(header_formats)
    column_format_string = ', '.join(column_formats)
    return {
        "output": {
            "description": "Write results to stdout. This is the default "
                           "behavior when --output-path is not specified.",
            "context": "ALL",
            "argument_type": "OPTIONAL_FLAG",
            "default": None,
            "category": "Output Control"
        },
        "output-path": {
            "description": "Path to which to write results.",
            "context": "ALL",
            "argument_type": "OPTION",
            "default": None,
            "category": "Output Control",
            "meta": {
                "accepts_file": True
            }
        },
        "output-columns": {
            "description": ("An ordered, comma-delimited list of columns to"
                            " include in the output. Available columns: "
                            + columns.get_options_as_string()
                            + f"\nCompatible formats: {column_format_string}"
                            ),
            "context": "ALL",
            "argument_type": "OPTION",
            "default": default_columns,
            "meta": {
                "separator": ","
            },
            "category": "Output Control"
        },
        "output-format": {
            "short_name": "m",
            "description": "Output format used for result data.",
            "context": "ALL",
            "argument_type": "OPTION",
            "default": default_format,
            "meta": {
                "valid_options": formats.get_options()
            },
            "category": "Output Control"
        },
        "output-headers": {
            "description": "Include column headers in "
                           "output.\n"
                           f"Compatible formats: {header_format_string}",
            "context": "ALL",
            "argument_type": "FLAG",
            "default": None,
            "category": "Output Control"
        }
    }


class ReportManager:

    def __init__(
                self,
                formats: Type[ReportFormatEnum],
                columns: Type[ReportColumnEnum],
                context: CliContext,
                read_stdin: Optional[bool],
                input_delimiter: Union[str, bytes],
                binary_input: bool = False
            ):
        self.formats = formats
        self.columns = columns
        self.context = context
        self.config = context.config
        self.read_stdin = read_stdin
        self.input_delimiter = input_delimiter
        self.binary_input = binary_input
        self.email_addresses = [] if self.config.email is None \
            else self.config.email
        self.io_manager = None

    def will_email(self) -> bool:
        return len(self.email_addresses) > 0

    def get_config_options(self) -> Dict[str, Dict[str, Any]]:
        return get_config_options(
                self.formats,
                self.columns
            )

    def get_io_manager(self) -> IoManager:
        if self.io_manager is None:
            self.io_manager = IoManager(
                    self.read_stdin,
                    self.input_delimiter,
                    self.config.output,
                    self.config.output_path,
                    binary=self.binary_input
                )
        return self.io_manager

    def open_output_file(self) -> Optional[IO]:
        mode = 'w+' if self.will_email() else 'w'
        return open(resolve_path(self.config.output_path), mode) \
            if self.config.output_path is not None \
            else nullcontext()

    def _instantiate_report(
                self,
                format: ReportFormat,
                columns: List[ReportColumn],
                email_addresses: List[str],
                mailer: Optional[Mailer],
                write_headers: bool
            ) -> Report:
        raise Exception(
                'Report instantiation must be implemented in a child class'
            )

    def _get_stdout_target(self) -> IO:
        return sys.stdout

    def _add_targets(
                self,
                report: Report,
                output_file: Optional[IO]
            ) -> None:
        if self.io_manager.should_write_stdout():
            report.add_target(self._get_stdout_target())
        if output_file is not None:
            report.add_target(
                    output_file,
                    os.path.basename(self.config.output_path)
                )

    def _get_configured_columns(self) -> List[ReportColumn]:
        columns = []
        for option in self.config.output_columns:
            if option == REPORT_COLUMNS_ALL:
                for column in self.columns:
                    columns.append(column)
            else:
                columns.append(self.columns.for_option(option))
        return columns

    def initialize_report(self, output_file: Optional[IO] = None) -> Report:
        format = self.formats.for_option(
                self.config.output_format
            )
        columns = self._get_configured_columns()
        mailer = self.context.get_mailer() if self.will_email() else None
        report = self._instantiate_report(
                format,
                columns,
                self.email_addresses,
                mailer,
                self.config.output_headers
            )
        report.has_custom_columns = self.config.is_specified('output_columns')
        self._add_targets(report, output_file)
        if not report.has_writers():
            raise ReportingException(
                    'Please specify an output file using the --output-path'
                    ' option or add --output to write results to standard '
                    'output'
                )
        return report
