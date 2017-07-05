#!/usr/bin/env python
#-*- coding: utf-8 -*-

import sys
sys.dont_write_bytecode = True
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
from Cython.Build import cythonize

__author__ = 'Leo Zhang'
__version__ = '0.0.1-dev'
__license__ = 'MIT'

setup(name='litefs',
      version=__version__,
      description='使用 Python 从零开始构建一个 Web 服务器框架。',
      long_description=(
      '使用 Python 从零开始构建一个 Web 服务器框架。 开发 Litefs 的是为了实现一个能'
      '快速、安全、灵活的构建 Web 项目的服务器框架。 litefs 是一个高性能的 Http 服务'
      '器。Litefs 具有高稳定性、丰富的功能、系统消耗低的特点。'),
      author=__author__,
      author_email='leafcoder@gmail.com',
      url='https://coding.net/u/leafcoder/p/litefs',
      py_modules=['litefs'],
      ext_modules=cythonize('litefs.py'),
      scripts=['litefs.py'],
      license='MIT',
      platforms='any',
      install_requires = open("requirements.pip").read().splitlines()
)
