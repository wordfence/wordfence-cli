import csv
import sys
from typing import IO, List, Any, Callable, Iterable, Type, Dict, Optional, \
        Union
from enum import Enum
from contextlib import nullcontext

from wordfence.logging import log
from wordfence.util.io import resolve_path
from .config import Config
from .io import IoManager


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
                raise ValueError(
                    'Only a single column can be written in this format'
                )
            self._target.write(value + self.delimiter)


class RowlessWriter(ReportWriter):

    def allows_headers(self) -> bool:
        return False

    def allows_column_customization(self) -> bool:
        return False

    def write_row(self, data: List[str]) -> None:
        pass

    def write_record(self, record) -> None:
        raise NotImplementedError()


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


class Report:

    def __init__(
                self,
                format: ReportFormat,
                columns: List[ReportColumn],
                write_headers: bool = False
            ):
        self.format = format.value
        self.columns = columns
        self.write_headers = write_headers
        self.headers_written = False
        self.writers = []
        self.has_custom_columns = False

    def add_target(self, stream: IO) -> None:
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
        self.writers.append(writer)

    def _write_row(self, data: List[str], record: ReportRecord):
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


def get_config_options(
            formats: Type[ReportFormatEnum],
            columns: Type[ReportColumnEnum],
            default_columns: List[ReportColumnEnum],
            default_format: str = 'csv'
        ) -> Dict[str, Dict[str, Any]]:
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
                           "behavior when --output-path is not specified. "
                           "Use --no-output to disable.",
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
            "category": "Output Control"
        },
        "output-columns": {
            "description": ("An ordered, comma-delimited list of columns to"
                            " include in the output. Available columns: "
                            + columns.get_options_as_string()
                            + f"\nCompatible formats: {column_format_string}"
                            ),
            "context": "ALL",
            "argument_type": "OPTION",
            "default": ','.join([column.header for column in default_columns]),
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
            "description": "Whether or not to include column headers in "
                           "output.\n"
                           f"Compatible formats: {header_format_string}",
            "context": "ALL",
            "argument_type": "FLAG",
            "default": None,
            "category": "Output Control"
        },
    }


class ReportManager:

    def __init__(
                self,
                formats: Type[ReportFormatEnum],
                columns: Type[ReportColumnEnum],
                config: Config,
                read_stdin: Optional[bool],
                input_delimiter: Union[str, bytes],
            ):
        self.formats = formats
        self.columns = columns
        self.config = config
        self.read_stdin = read_stdin
        self.input_delimiter = input_delimiter
        self.io_manager = None
        self.context = None

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
                    self.config.output_path
                )
        return self.io_manager

    def open_output_file(self) -> Optional[IO]:
        return open(resolve_path(self.config.output_path), 'w') \
                if self.config.output_path is not None \
                else nullcontext()

    def _instantiate_report(
                self,
                format: ReportFormat,
                columns: List[ReportColumn],
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
            report.add_target(output_file)

    def initialize_report(self, output_file: Optional[IO] = None) -> Report:
        format = self.formats.for_option(
                self.config.output_format
            )
        columns = [
                self.columns.for_option(option) for option
                in self.config.output_columns
            ]
        report = self._instantiate_report(
                format,
                columns,
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
