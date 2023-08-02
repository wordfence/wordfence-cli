#!/usr/bin/env python3

from distutils.core import setup
from wordfence import version

setup(name='Wordfence CLI',
      version=version.__version__,
      description='Command-line malware scanner powered by Wordfence',
      py_modules=[],
      )
