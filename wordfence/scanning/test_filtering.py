import unittest

from wordfence.scanning import filtering


class FileFilterTests(unittest.TestCase):

    def test_filter_any_allows_non_images(self):
        file_filter = filtering.FileFilter()
        file_filter.add(filtering.filter_any)
        file_filter.add(filtering.filter_images, False)
        self.assertTrue(file_filter.filter(b'/tmp/allowed.php'))

    def test_filter_any_deny_images(self):
        file_filter = filtering.FileFilter()
        file_filter.add(filtering.filter_any)
        file_filter.add(filtering.filter_images, False)
        self.assertFalse(file_filter.filter(b'/tmp/image.jpg'))


if __name__ == '__main__':
    unittest.main()
