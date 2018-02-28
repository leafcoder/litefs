#!/usr/bin/env python
#-*- coding: utf-8 -*-

import sys
sys.dont_write_bytecode = True

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
from Cython.Build import cythonize

long_description = '''
使用 Python 从零开始构建一个 Web 服务器框架。 开发 Litefs 的是为了实现一个能快速、\
安全、灵活的构建 Web 项目的服务器框架。 litefs 是一个高性能的 Http 服务器。Litefs 具\
有高稳定性、丰富的功能、系统消耗低的特点。

Name: leozhang
Email: leafcoder@gmail.com

Copyright (c) 2017, Leafcoder.
License: MIT (see LICENSE for details)
'''

version_major = 0
version_minor = 2
version_build = 0
__version__ = '%s.%s.%s' % (version_major, version_minor, version_build)
__author__  = 'Leafcoder'
__license__ = 'MIT'

setup(
    name='litefs',
    version=__version__,
    description='使用 Python 从零开始构建一个 Web 服务器框架。',
    long_description=__doc__,
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
