import unittest
from types import SimpleNamespace
from unittest import mock

from wordfence.cli.reporting import ReportManager
from wordfence.cli.dbscan.reporting import (
        DatabaseScanReportFormat,
        DatabaseScanReportColumn
    )


class ReportManagerEncodingTest(unittest.TestCase):

    def test_open_output_file_uses_utf8_encoding(self):
        config = SimpleNamespace(
                output=None,
                output_path='/tmp/out.csv',
                email=None
            )
        context = SimpleNamespace(config=config)
        manager = ReportManager(
                DatabaseScanReportFormat,
                DatabaseScanReportColumn,
                context,
                read_stdin=None,
                input_delimiter='\0'
            )

        patcher = mock.patch(
                'wordfence.cli.reporting.open',
                mock.mock_open()
            )
        with patcher as mock_open:
            manager.open_output_file()

        _, kwargs = mock_open.call_args
        self.assertEqual('utf-8', kwargs.get('encoding'))


if __name__ == '__main__':
    unittest.main()
