import os
import mmap
import math

from typing import Optional


class DirectIoBuffer:

    def __init__(self, max_chunk_size: int = mmap.PAGESIZE):
        self.max_chunk_size = max_chunk_size
        self.buffer_size = (
                math.ceil(max_chunk_size / mmap.PAGESIZE) * mmap.PAGESIZE
            )
        self.buffer = mmap.mmap(-1, self.buffer_size)
        self.buffer_view = memoryview(self.buffer)
        self.buffers = [self.buffer]

    def seek(self, position: int = 0) -> list:
        self.buffer.seek(position)

    def read(self, length: int) -> bytes:
        return self.buffer.read(length)


class DirectIoReader:

    def __init__(self, path: str, buffer: DirectIoBuffer):
        self.fd = os.open(path, os.O_RDONLY | os.O_DIRECT)
        self.buffer = buffer
        self.offset = 0

    def read(self, limit: Optional[int] = None) -> bytes:
        read_offset = math.floor(self.offset / mmap.PAGESIZE) * mmap.PAGESIZE
        skip = self.offset % mmap.PAGESIZE
        read_length = os.preadv(self.fd, self.buffer.buffers, read_offset)
        read_length -= skip
        read_length = min(read_length, limit)
        self.offset += read_length
        self.buffer.seek(skip)
        return self.buffer.read(read_length)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        os.close(self.fd)
