import sys
from typing import Optional, Union

from ..util.io import StreamReader


class IoManager:

    def __init__(
                self,
                read_stdin: Optional[bool],
                input_delimiter: Union[str, bytes],
                write_stdout: Optional[bool] = None,
                output_path: Optional[str] = None,
                encode_paths: bool = False,
                binary: bool = False
            ):
        self.read_stdin = read_stdin
        if binary:
            self.input_delimiter = input_delimiter \
                if isinstance(input_delimiter, bytes) \
                else input_delimiter.encode('utf-8')
        else:
            self.input_delimiter = input_delimiter \
                if isinstance(input_delimiter, str) \
                else input_delimiter.decode('utf-8')
        self.write_stdout = write_stdout
        self.output_path = output_path
        self.binary = binary

    def should_read_stdin(self) -> bool:
        if sys.stdin is None:
            return False
        if self.read_stdin is None:
            return not sys.stdin.isatty()
        else:
            return self.read_stdin

    def get_input_reader(self) -> StreamReader:
        if not hasattr(self, 'input_reader'):
            self.input_reader = StreamReader(
                    sys.stdin,
                    self.input_delimiter,
                    binary=self.binary
                )
        return self.input_reader

    def should_write_stdout(self) -> bool:
        if sys.stdout is None or self.write_stdout is False:
            return False
        return self.write_stdout or self.output_path is None
