#!/usr/bin/env python
#-*- coding: utf-8 -*-

import sys
sys.dont_write_bytecode = True

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
from Cython.Build import cythonize

import litefs

__author__  = litefs.__author__
__version__ = litefs.__version__
__license__ = litefs.__license__

print litefs.__doc__
setup(
    name='litefs',
    version=__version__,
    description='使用 Python 从零开始构建一个 Web 服务器框架。',
    long_description=litefs.__doc__,
    author=__author__,
    author_email='leafcoder@gmail.com',
    url='https://github.com/leafcoder/litefs',
    py_modules=['litefs'],
    ext_modules=cythonize('litefs.py'),
    scripts=['litefs.py'],
    license=__license__,
    platforms='any',
    install_requires=open("requirements.pip").read().splitlines()
)
