import unittest

from .versioning import compare_php_versions


class TestPhpVersions(unittest.TestCase):

    def _expect_comparison(
                self,
                a: str,
                b: str,
                expected: int
            ) -> None:
        self.assertEqual(
                compare_php_versions(a, b),
                expected
            )

    def test_numeric(self):
        self._expect_comparison('1.0.0', '1.0.0', 0)
        self._expect_comparison('2.0.0', '3.0.0', -1)
        self._expect_comparison('5.0.0', '4.0.0', 1)

    def test_short(self):
        self._expect_comparison('1.0', '1.0.0', 0)
        self._expect_comparison('2.0.0', '2', 0)
        self._expect_comparison('1', '2', -1)

    def test_dev_versions(self):
        self._expect_comparison('1.0.0-rc1', '1.0.0', -1)
        self._expect_comparison('2.0.dev', '2.0', -1)
        self._expect_comparison('1.0.0-test', '1.0.0-dev', -1)
        self._expect_comparison('1.0.0-alpha', '1.0.0-dev', 1)
        self._expect_comparison('3.45.beta', '3.45.alpha', 1)
        self._expect_comparison('5.0.0.beta', '5.0.0.rc', -1)
        self._expect_comparison('9.0.0', '9.0.0rc1', 1)
        self._expect_comparison('10.0.0', '10.0.0pl', -1)
        self._expect_comparison('1.0-dev', '1.0.0-dev', -1)
        self._expect_comparison('1.0.0-rc', '1.0.0-RC', 0)
        self._expect_comparison('1.0.0-alpha', '1.0.0-a', 0)
        self._expect_comparison('1.0.0-beta', '1.0.0b', 0)
        self._expect_comparison('1.0.0-pl', '1.0.0-p', 0)
