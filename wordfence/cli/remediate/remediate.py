import os

from ...wordpress.remediator import Remediator, Noc1RemediationSource
from ...logging import log
from ..subcommands import Subcommand
from ..exceptions import ConfigurationException
from .reporting import RemediationReportManager, RemediationReport


class RemediateSubcommand(Subcommand):

    def prepare(self) -> None:
        self.remediator = Remediator(
                Noc1RemediationSource(self.context.get_noc1_client())
            )

    def process_path(self, path: bytes, report: RemediationReport) -> None:
        log.debug(f'Attempting to remediate {path}...')
        for result in self.remediator.remediate(os.fsencode(path)):
            report.add_result(result)

    def invoke(self) -> int:
        report_manager = RemediationReportManager(self.context)
        io_manager = report_manager.get_io_manager()
        with report_manager.open_output_file() as output_file:
            report = report_manager.initialize_report(output_file)
            for path in self.config.trailing_arguments:
                self.process_path(path, report)
            if io_manager.should_read_stdin():
                reader = io_manager.get_input_reader()
                for path in reader.read_all_entries():
                    self.process_path(path, report)
            if self.remediator.input_count == 0 and \
                    self.context.requires_input(self.config.require_path):
                raise ConfigurationException(
                        'At least one path to remediate must be specified'
                    )
            report.complete()
            if report.counts.remediated == report.counts.total:
                log.info(
                        f'{report.counts.remediated} file(s) were successfully'
                        ' remediated'
                    )
            else:
                log.error(
                    f'{report.counts.remediated} of {report.counts.total} '
                    'file(s) were successfully remediated, '
                    f'{report.counts.unsuccessful} file(s) could not be '
                    'remediated'
                )
                return 1
        return 0


factory = RemediateSubcommand
