#!/usr/bin/env python
#-*- coding: utf-8 -*-

import sys
sys.dont_write_bytecode = True

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
try:
    from Cython.Build import cythonize
except ImportError:
    import os
    os.system('pip install cython')
    from Cython.Build import cythonize

long_description = '''\
Build a web server framework using Python. Litefs was developed to imple\
ment a server framework that can quickly, securely, and flexibly build Web \
projects. Litefs is a high-performance HTTP server. Litefs has the characte\
ristics of high stability, rich functions, and low system consumption.

Name: leafcoder
Email: leafcoder@gmail.com

Copyright (c) 2017, Leafcoder.
License: MIT (see LICENSE for details)
'''

__version__ = '0.3.0'
__author__  = 'Leafcoder'
__license__ = 'MIT'

language_level = 2
if sys.version_info[0] > 2:
    language_level = 3

setup(
    name='litefs',
    version=__version__,
    description='Build a web server framework using Python.',
    long_description=__doc__,
    author=__author__,
    author_email='leafcoder@gmail.com',
    url='https://github.com/leafcoder/litefs',
    py_modules=['litefs'],
    ext_modules=cythonize(
        'litefs.py',
        compiler_directives={
            'language_level' : language_level
        }
    ),
    license=__license__,
    platforms='any',
    package_data={
        '': ["*.txt", 'LICENSE'],
        'site': ['site/*', '*.py']
    },
    install_requires=open('requirements.txt').read().split('\n')
)
