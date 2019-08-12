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
使用 Python 从零开始构建一个 Web 服务器框架。 开发 Litefs 的是为了实现一个能快速、安\
全、灵活的构建 Web 项目的服务器框架。 Litefs 是一个高性能的 HTTP 服务器。Litefs 具有高\
稳定性、丰富的功能、系统消耗低的特点。

Name: leafcoder
Email: leafcoder@gmail.com

Copyright (c) 2017, Leafcoder.
License: MIT (see LICENSE for details)
'''

__version__ = '0.2.5'
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
    license=__license__,
    platforms='any',
    package_data={
        '': ["*.txt", 'LICENSE'],
        'demo': ['site/*', '*.py']
    },
    install_requires=[
        'Mako==1.0.6',
        'MarkupSafe==1.0',
        'greenlet==0.4.13',
        'PyYAML==3.12',
        'argh==0.26.2',
        'argparse==1.2.1',
        'pathtools==0.1.2',
        'watchdog==0.8.3',
        'wsgiref==0.1.2'
    ]
)
