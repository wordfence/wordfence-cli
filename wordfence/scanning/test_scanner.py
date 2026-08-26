import os
import queue
import tempfile
import unittest

from wordfence.scanning.filtering import FileFilter, filter_any
from wordfence.scanning.scanner import FileLocator


class FileLocatorTests(unittest.TestCase):

    def test_does_not_follow_symlinks_outside_scan_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = os.path.join(directory, 'root')
            outside = os.path.join(directory, 'outside')
            os.mkdir(root)
            os.mkdir(outside)
            outside_file = os.path.join(outside, 'secret.php')
            with open(outside_file, 'wb') as file:
                file.write(b'<?php')
            os.symlink(outside, os.path.join(root, 'linked-directory'))

            paths = queue.SimpleQueue()
            file_filter = FileFilter()
            file_filter.add(filter_any)
            locator = FileLocator(
                    os.fsencode(root),
                    paths,
                    file_filter,
                )
            locator.locate()

            self.assertTrue(paths.empty())


if __name__ == '__main__':
    unittest.main()
