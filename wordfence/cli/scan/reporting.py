import csv
from typing import IO, List, Any
from enum import Enum

from wordfence.scanning.scanner import ScanResult
from wordfence.intel.signatures import SignatureSet, Signature


class ReportColumn(str, Enum):
    FILENAME = 'filename'
    SIGNATURE_ID = 'signature_id'
    SIGNATURE_NAME = 'signature_name'
    SIGNATURE_DESCRIPTION = 'signature_description'
    MATCHED_TEXT = 'matched_text'

    def get_valid_options() -> List[str]:
        return [column.value for column in ReportColumn]

    def get_valid_options_as_string(delimiter: str = ', '):
        return delimiter.join(ReportColumn.get_valid_options())


class ReportFormat(str, Enum):
    CSV = 'csv',
    TSV = 'tsv',
    NULL_DELIMITED = 'null-delimited',
    LINE_DELIMITED = 'line-delimited',
    HUMAN = 'human'

    def get_valid_options() -> List[str]:
        return [format.value for format in ReportFormat]


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


class HumanReadableWriter(ReportWriter):

    def __init__(self, target: IO, columns: str):
        super().__init__(target)
        self._columns = columns

    def _get_value(data: List[str], column: str) -> str:
        return

    def _map_data_to_dict(self, data: List[str]) -> dict:
        return {
            name: data[index] for index, name in enumerate(self._columns)
        }

    def write_row(self, data: List[str]) -> None:
        values = self._map_data_to_dict(data)
        file = None
        signature_id = None
        if 'filename' in values:
            file = values['filename']
        if 'signature_id' in values:
            signature_id = values['signature_id']
        # TODO: Add more custom messages if desired
        if file is not None:
            if signature_id is not None:
                self._target.write(
                        f"File at {file} matched signature {signature_id}"
                    )
            else:
                self._target.write(
                        f"File {file} matched a signature"
                    )
        else:
            self._target.write(
                    "Match found: " + str(values)
                )
        self._target.write("\n")

    def allows_headers(self) -> bool:
        return False


class Report:

    def __init__(
                self,
                format: ReportFormat,
                columns: List[str],
                signature_set: SignatureSet,
                write_headers: bool = False
            ):
        self.format = format
        self.columns = columns
        self.signature_set = signature_set
        self.write_headers = write_headers
        self.headers_written = False
        self.writers = []

    def _initialize_writer(self, stream: IO) -> ReportWriter:
        if self.format == ReportFormat.CSV:
            return CsvReportWriter(stream)
        elif self.format == ReportFormat.TSV:
            return TsvReportWriter(stream)
        elif self.format == ReportFormat.NULL_DELIMITED:
            return SingleColumnWriter(stream, "\0")
        elif self.format == ReportFormat.LINE_DELIMITED:
            return SingleColumnWriter(stream, "\n")
        elif self.format == ReportFormat.HUMAN:
            return HumanReadableWriter(stream, self.columns)
        else:
            raise ValueError('Unsupported report format: ' + str(self.format))

    def add_target(self, stream: IO) -> None:
        writer = self._initialize_writer(stream)
        self.writers.append(writer)

    def _get_column_value(
                self,
                column: str,
                result: ScanResult,
                signature: Signature,
                match: str
            ) -> Any:
        if column == ReportColumn.FILENAME.value:
            return result.path
        elif column == ReportColumn.SIGNATURE_ID.value:
            return signature.identifier
        elif column == ReportColumn.SIGNATURE_NAME.value:
            return signature.name
        elif column == ReportColumn.SIGNATURE_DESCRIPTION.value:
            return signature.description
        elif column == ReportColumn.MATCHED_TEXT.value:
            return match,
        elif column == 'discovered_at':
            return int(result.timestamp)
        else:
            raise ValueError(f'Unrecognized column: {column}')

    def _format_result(self, result: ScanResult) -> List[List[str]]:
        rows = []
        for signature_id, match in result.matches.items():
            signature = self.signature_set.get_signature(signature_id)
            row = []
            for column in self.columns:
                value = self._get_column_value(
                        column,
                        result,
                        signature,
                        match
                    )
                row.append(value)
            rows.append(row)
        return rows

    def _write_row(self, data: List[str]):
        for writer in self.writers:
            writer.write_row(data)

    def _write_headers(self) -> None:
        if self.headers_written or not self.write_headers:
            return
        for writer in self.writers:
            if writer.allows_headers():
                writer.write_row(self.columns)

    def add_result(self, result: ScanResult) -> None:
        self._write_headers()
        rows = self._format_result(result)
        for row in rows:
            for writer in self.writers:
                writer.write_row(row)

    def has_writers(self) -> bool:
        return len(self.writers) > 0
