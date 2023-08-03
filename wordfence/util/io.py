from typing import Optional, TextIO


class StreamReader:

    def __init__(self, stream: TextIO, delimiter: str, chunk_size: int = 1024):
        self.stream = stream
        self.delimiter = delimiter
        print('Delimiter: ' + repr(self.delimiter))
        self.chunk_size = chunk_size
        self._buffer = ''
        self._end_of_stream = False

    def read_entry(self) -> Optional[str]:
        while True:
            index = self._buffer.find(self.delimiter)
            if index != -1:
                entry = self._buffer[:index]
                self._buffer = self._buffer[index + 1:]
                return entry
            elif not self._end_of_stream:
                read = self.stream.read(self.chunk_size)
                if read == '':
                    self._end_of_stream = True
                self._buffer += read
            else:
                break
        if len(self._buffer) > 0:
            path = self._buffer
            self._buffer = ''
            return path
        else:
            return None
